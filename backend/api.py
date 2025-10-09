import os
import sys
import uuid
from typing import Optional
from PyPDF2 import PdfReader
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiofiles
import bcrypt
import requests
from celery.result import AsyncResult
import json

# DB helpers
from backend.db import get_db, remove_domain, get_client_by_domain, register_domain as db_register_domain
from backend.db import get_tasks_for_client
# JWT Authentication
from backend.auth_utils import create_jwt, get_client_from_header

# Celery
from backend.tasks import crawl_website_task, run_embeddings_task, crawl_and_embed_pipeline, pdf_embed_pipeline
from backend.celery_app import celery_app

# Add Chatbot/LLM path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/llm"))
sys.path.append(CHATBOT_LLM_DIR)
from llm_service import chat_with_model, explain_context

# === FastAPI App ===
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
CLIENTS_DIR = os.path.join(BASE_DIR, "client_data")
os.makedirs(CLIENTS_DIR, exist_ok=True)


# ----------------------------
# Models
# ----------------------------
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class CrawlRequest(BaseModel):
    allowed_domain: str
    start_url: str


class SignupRequest(BaseModel):
    name: str
    username: str
    password: str
    mobile: str
    email: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


# ----------------------------
# AUTH
# ----------------------------
@app.post("/auth/signup")
async def signup(req: SignupRequest):
    conn = get_db()
    cursor = conn.cursor()
    client_id = f"{req.username}_{uuid.uuid4().hex[:6]}"
    hashed_password = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    try:
        cursor.execute(
            """
            INSERT INTO users (username, password, name, email, mobile, client_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (req.username, hashed_password, req.name, req.email, client_id, req.mobile),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")
    finally:
        conn.close()
    token = create_jwt(client_id)
    return {"success": True, "token": token, "client_id": client_id, "message": "Signup successful"}


@app.post("/auth/login")
async def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (req.username,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    stored_password = user["password"]
    if isinstance(stored_password, bytes):
        stored_password = stored_password.decode()
    if not bcrypt.checkpw(req.password.encode(), stored_password.encode()):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_jwt(user["client_id"])
    return {"success": True, "token": token, "client_id": user["client_id"], "message": "Login successful"}


@app.get("/auth/me")
async def get_me(client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, username, email FROM users WHERE client_id=?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client_id": client_id, "name": row["name"], "username": row["username"], "email": row["email"]}



# ----------------------------
# CLIENT CHAT
# ----------------------------

from fastapi import Request, Header, HTTPException
from typing import Optional


@app.post("/client/chat/{client_id}")
def client_chat(client_id: str, req: ChatRequest, request: Request, x_chatbot_key: str = Header(None)):

    # Connect to the database
    conn = get_db()
    cursor = conn.cursor()

    # ✅ Validate client + chatbot_key
    cursor.execute("SELECT * FROM users WHERE client_id=? AND chatbot_key=?", (client_id, x_chatbot_key))
    client = cursor.fetchone()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # ✅ Ensure session_id
    session_id = req.session_id or str(uuid.uuid4())

    # ✅ Capture user-agent and IP address
    user_agent = request.headers.get("user-agent", "unknown")
    user_ip = request.client.host

    # Get the user's location from ipinfo.io API
    try:
        location_response = requests.get(f"https://ipinfo.io/{user_ip}/json")
        location_data = location_response.json()
        country_code = location_data.get("country", "Unknown")
    except requests.RequestException:
        country_code = "Unknown"

    # ✅ Store user message and country code in the database
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_id, session_id, "user", req.message, user_agent, country_code))
    conn.commit()

    # ✅ Generate chatbot reply
    bot_reply = chat_with_model(client_id, req.message)

    # ✅ Store assistant reply with the same country code
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_id, session_id, "assistant", bot_reply, user_agent, country_code))
    conn.commit()

    # Close the connection
    conn.close()

    # Return the response with session_id and bot reply
    return {"session_id": session_id, "reply": bot_reply}


# ----------------------------
# 🔹 CHAT CONTEXT
# ----------------------------

@app.post("/client/context/{client_id}")
def context_endpoint(client_id: str, req: ChatRequest, x_chatbot_key: str = Header(None)):

    # Connect to the database
    conn = get_db()
    cursor = conn.cursor()

    # ✅ Validate client + chatbot_key
    cursor.execute("SELECT * FROM users WHERE client_id=? AND chatbot_key=?", (client_id, x_chatbot_key))
    client = cursor.fetchone()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # ✅ Fetch and explain context for the user
    ctx = explain_context(client_id, req.message)

    # Return context or a default message if no context found
    return {"context": ctx or "No relevant context found."}



@app.get("/client/chats/me")
async def get_chats(session_id: str, client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT session_id, role, message, user_agent, country_code, created_at
        FROM chats
        WHERE client_id=? AND session_id=?
        ORDER BY created_at ASC
    """,
        (client_id, session_id),
    )
    chats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"chats": chats}


# @app.post("/client/context/me")
# async def context(req: ChatRequest, client_id: str = Depends(get_client_from_header)):
#     ctx = explain_context(client_id, req.message)
#     return {"context": ctx or "No relevant context found."}


# ----------------------------
# DOMAIN MANAGEMENT
# ----------------------------
@app.get("/client/domains/me")
async def get_domains(client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT domain, created_at FROM domain_mappings WHERE client_id=? ORDER BY created_at DESC",
        (client_id,),
    )
    domains = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"domains": domains}


@app.get("/client/lookup-by-domain")
def lookup_client_by_domain(domain: str):
    result = get_client_by_domain(domain)
    if not result:
        raise HTTPException(status_code=404, detail="Domain not found")
    return {
        "client_id": result["client_id"],
        "chatbot_key": result["chatbot_key"],
        "client_name": result["client_name"],
    }


@app.post("/client/register-my-domains/me")
async def register_domains(domains: list[str], client_id: str = Depends(get_client_from_header)):
    registered, failed = [], []
    for d in domains:
        if db_register_domain(d, client_id):
            clean = d.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
            registered.append(clean)
        else:
            failed.append(d)
    return {"success": len(failed) == 0, "registered_domains": registered, "failed_domains": failed}


@app.delete("/client/domains/me/{domain}")
async def delete_domain(domain: str, client_id: str = Depends(get_client_from_header)):
    if not remove_domain(domain, client_id):
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
    return {"success": True, "message": f"Domain '{domain}' deleted"}


# ----------------------------
# CLIENT MANAGEMENT
# ----------------------------
@app.get("/admin/clients")
async def list_clients():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT client_id, username, name, email FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"clients": users}


@app.get("/client/me")
async def get_client(client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, username, email FROM users WHERE client_id=?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"name": row["name"], "username": row["username"], "email": row["email"]}


# ----------------------------
# CHAT HISTORY
# ----------------------------
@app.get("/client/sessions/me")
async def get_sessions(client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT session_id FROM chats WHERE client_id=? ORDER BY created_at DESC",
        (client_id,),
    )
    sessions = [row["session_id"] for row in cursor.fetchall()]
    conn.close()
    return {"sessions": sessions}


# ----------------------------
# CRAWL, EMBED, PIPELINE (Celery)
# ----------------------------
# @app.post("/client/me/crawl-and-embed", response_model=TaskResponse)
# async def crawl_and_embed(req: CrawlRequest, client_id: str = Depends(get_client_from_header)):
#     task = crawl_and_embed_pipeline.apply_async(args=[client_id, req.allowed_domain, req.start_url])
#     return TaskResponse(task_id=task.id, status="queued", message="Crawl+embed task queued.")



@app.post("/client/me/crawl-and-embed", response_model=TaskResponse)
async def crawl_and_embed(req: CrawlRequest, client_id: str = Depends(get_client_from_header)):
    task = crawl_and_embed_pipeline.delay(client_id, req.allowed_domain, req.start_url)
    return TaskResponse(task_id=task.id, status="queued", message="Crawl+embed task queued.")


@app.post("/client/me/crawl", response_model=TaskResponse)
async def crawl_only(req: CrawlRequest, client_id: str = Depends(get_client_from_header)):
    task = crawl_website_task.apply_async(args=[client_id, req.allowed_domain, req.start_url])
    return TaskResponse(task_id=task.id, status="queued", message="Crawl task queued.")


@app.post("/client/me/embed", response_model=TaskResponse)
async def embed_only(client_id: str = Depends(get_client_from_header)):
    task = run_embeddings_task.apply_async(args=[client_id])
    return TaskResponse(task_id=task.id, status="queued", message="Embeddings task queued.")


from celery.result import AsyncResult
@app.get("/client/me/tasks")
async def list_tasks(client_id: str = Depends(get_client_from_header)):
    """
    Return full history of tasks for this client, newest first.
    """
    tasks = get_tasks_for_client(client_id)
    return {"tasks": tasks}




@app.get("/client/me/task-status/{task_id}")
async def get_task_status(task_id: str, client_id: str = Depends(get_client_from_header)):
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return {"status": "pending"}
    elif result.state == "STARTED":
        return {"status": "running", "info": result.info}
    elif result.state == "PROGRESS":
        return {"status": "running", "info": result.info}
    elif result.state == "SUCCESS":
        return {"status": "completed", "result": result.result}
    elif result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    else:
        return {"status": result.state.lower(), "info": result.info}


# ----------------------------
# UPLOAD QA
# ----------------------------
# @app.post("/client/upload-qa/me")
# async def upload_qa(file: UploadFile = File(...), client_id: str = Depends(get_client_from_header)):
#     client_dir = os.path.join(CLIENTS_DIR, client_id)
#     os.makedirs(client_dir, exist_ok=True)
#     file_path = os.path.join(client_dir, "custom_qa.json")

#     async with aiofiles.open(file_path, "ab") as f:
#         content = await file.read()
#         await f.write(content)

#     # Clear cache directly
#     try:
#         from llm_service import _load_custom_qa_cached
#         _load_custom_qa_cached.cache_clear()
#     except Exception:
#         pass

#     return {"status": "success", "message": f"Uploaded Q&A for {client_id} - cache refreshed"}



@app.post("/client/upload-qa/me")
async def upload_qa(file: UploadFile = File(...), client_id: str = Depends(get_client_from_header)):
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_dir, exist_ok=True)
    file_path = os.path.join(client_dir, "custom_qa.json")

    # Read new uploaded JSON
    content = await file.read()
    new_data = json.loads(content.decode("utf-8"))

    # Ensure it's always a list
    if not isinstance(new_data, list):
        new_data = [new_data]

    # Load existing data if file exists
    if os.path.exists(file_path):
        async with aiofiles.open(file_path, "r") as f:
            old_content = await f.read()
            try:
                old_data = json.loads(old_content)
                if not isinstance(old_data, list):
                    old_data = [old_data]
            except Exception:
                old_data = []
    else:
        old_data = []

    # Merge
    merged_data = old_data + new_data

    # Save back
    async with aiofiles.open(file_path, "w") as f:
        await f.write(json.dumps(merged_data, indent=2))

    # Clear cache
    try:
        from llm_service import _load_custom_qa_cached
        _load_custom_qa_cached.cache_clear()
    except Exception:
        pass

    return {"status": "success", "message": f"Uploaded Q&A for {client_id} - merged and cache refreshed"}



@app.post("/client/upload-pdf/me")
async def upload_pdf(file: UploadFile = File(...), client_id: str = Depends(get_client_from_header)):
    """Upload and extract text from a PDF file."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_dir, exist_ok=True)
    # id=0
    # id = id+1
    # Save the PDF file
    pdf_path = os.path.join(client_dir, "custom_pdf.pdf")
    async with aiofiles.open(pdf_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    
    try:
        # Extract text from PDF using PyPDF2
        reader = PdfReader(pdf_path)
        text_content = ""
        
        for page in reader.pages:
            text_content += page.extract_text() + "\n\n"
        
        # Save extracted text
        text_path = os.path.join(client_dir, "custom_pdf.txt")
        async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
            await f.write(text_content)
        
        return {
            "status": "success", 
            "message": f"PDF uploaded and text extracted for {client_id}",
            "pages_extracted": len(reader.pages),
            "text_length": len(text_content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {str(e)}")


@app.post("/client/me/embed-pdf", response_model=TaskResponse)
async def embed_pdf(client_id: str = Depends(get_client_from_header)):
    """Start embedding process for uploaded PDF."""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    pdf_text_path = os.path.join(client_dir, "custom_pdf.txt")
    
    if not os.path.exists(pdf_text_path):
        raise HTTPException(status_code=404, detail="No PDF text found. Please upload a PDF first.")
    
    task = pdf_embed_pipeline.delay(client_id)
    return TaskResponse(task_id=task.id, status="queued", message="PDF embedding task queued.")


@app.get("/client/pdf-status/me")
async def check_pdf_status(client_id: str = Depends(get_client_from_header)):
    """Check PDF processing status."""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    return {
        "pdf_uploaded": os.path.exists(os.path.join(client_dir, "custom_pdf.pdf")),
        "text_extracted": os.path.exists(os.path.join(client_dir, "custom_pdf.txt")),
        "embedded": os.path.exists(os.path.join(client_dir, "embeddings.json")),
    }



@app.get("/client/status/me")
async def check_status(client_id: str = Depends(get_client_from_header)):
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    return {
        "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
        "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
        "embedded": True,
    }


@app.get("/client/view-qa/me")
async def view_qa(client_id: str = Depends(get_client_from_header)):
    """View uploaded Q&A content"""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    qa_path = os.path.join(client_dir, "custom_qa.json")
    
    if not os.path.exists(qa_path):
        return {
            "has_qa": False,
            "qa_data": [],
            "message": "No Q&A file found"
        }
    
    try:
        async with aiofiles.open(qa_path, "r", encoding="utf-8") as f:
            content = await f.read()
            qa_data = json.loads(content)
        
        return {
            "has_qa": True,
            "qa_data": qa_data,
            "qa_count": len(qa_data),
            "message": f"Found {len(qa_data)} Q&A pairs"
        }
    except Exception as e:
        return {
            "has_qa": False,
            "qa_data": [],
            "error": str(e),
            "message": "Error reading Q&A file"
        }



@app.get("/client/view-pdf-info/me")
async def view_pdf_info(client_id: str = Depends(get_client_from_header)):
    """View PDF upload information"""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    pdf_path = os.path.join(client_dir, "custom_pdf.pdf")
    text_path = os.path.join(client_dir, "custom_pdf.txt")
    
    result = {
        "has_pdf": os.path.exists(pdf_path),
        "has_extracted_text": os.path.exists(text_path),
        "pdf_info": {}
    }
    
    if result["has_pdf"]:
        try:
            # Get PDF file info
            pdf_stat = os.stat(pdf_path)
            result["pdf_info"] = {
                "filename": "custom_pdf.pdf",
                "size_bytes": pdf_stat.st_size,
                "size_mb": round(pdf_stat.st_size / (1024 * 1024), 2),
                "uploaded_date": pdf_stat.st_mtime
            }
            
            # Get text extraction info if available
            if result["has_extracted_text"]:
                try:
                    async with aiofiles.open(text_path, "r", encoding="utf-8") as f:
                        text_content = await f.read()
                    
                    result["pdf_info"]["text_length"] = len(text_content)
                    result["pdf_info"]["word_count"] = len(text_content.split())
                    result["pdf_info"]["preview"] = text_content[:500] + "..." if len(text_content) > 500 else text_content
                except Exception:
                    result["pdf_info"]["text_extraction_error"] = "Could not read extracted text"
            
        except Exception as e:
            result["pdf_info"]["error"] = str(e)
    
    return result


@app.delete("/client/delete-qa/me")
async def delete_qa(client_id: str = Depends(get_client_from_header)):
    """Delete Q&A file"""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    qa_path = os.path.join(client_dir, "custom_qa.json")
    
    if not os.path.exists(qa_path):
        raise HTTPException(status_code=404, detail="No Q&A file found")
    
    try:
        os.remove(qa_path)
        
        # Clear cache
        from llm_service import reload_custom_qa_cache
        reload_custom_qa_cache(client_id)
        
        return {"success": True, "message": "Q&A file deleted and cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Q&A file: {str(e)}")


@app.delete("/client/delete-pdf/me")
async def delete_pdf(client_id: str = Depends(get_client_from_header)):
    """Delete PDF files"""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    pdf_path = os.path.join(client_dir, "custom_pdf.pdf")
    text_path = os.path.join(client_dir, "custom_pdf.txt")
    
    deleted_files = []
    errors = []
    
    for file_path, file_type in [(pdf_path, "PDF"), (text_path, "extracted text")]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted_files.append(file_type)
            except Exception as e:
                errors.append(f"Failed to delete {file_type}: {str(e)}")
    
    if not deleted_files:
        raise HTTPException(status_code=404, detail="No PDF files found")
    
    result = {"success": True, "deleted_files": deleted_files}
    if errors:
        result["errors"] = errors
    
    return result