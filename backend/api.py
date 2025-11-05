import os
import sys
import uuid
import random
from typing import Optional, List
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiofiles
import bcrypt
import requests
from celery.result import AsyncResult
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
import threading
import time


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
    allow_origins=["*"],
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


class DailyStats(BaseModel):
    date: str
    visitors: int
    chats: int


class StatsResponse(BaseModel):
    daily_stats: List[DailyStats]

class AdminReplyRequest(BaseModel):
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

    # ✅ Store user message with admin_override and is_active columns
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code, admin_override, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 0, 1)
    """, (client_id, session_id, "user", req.message, user_agent, country_code))
    conn.commit()

    # ✅ Generate chatbot reply
    bot_response = chat_with_model(client_id, req.message)

    # Extract just the answer text from the response dictionary
    bot_reply = bot_response.get("answer", "I'm sorry, I couldn't generate a response.") if isinstance(bot_response, dict) else str(bot_response)

    # ✅ Store assistant reply with admin_override and is_active columns
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code, admin_override, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 0, 1)
    """, (client_id, session_id, "assistant", bot_reply, user_agent, country_code))
    conn.commit()

    # Close the connection
    conn.close()

    # Return the response with session_id and bot reply (with full metadata)
    return {
        "session_id": session_id,
        "reply": bot_reply,
        "confidence": bot_response.get("confidence") if isinstance(bot_response, dict) else None,
        "type": bot_response.get("type") if isinstance(bot_response, dict) else None
    }

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
    cursor.execute("""
        SELECT * FROM chats
        WHERE client_id=? AND session_id=? AND is_active=1
        ORDER BY created_at ASC
    """, (client_id, session_id))
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
# DAILY STATS ENDPOINT
# ----------------------------
#
active_users_lock = threading.Lock()
# In-memory store for active users (use Redis in production)
active_users: Dict[str, Dict] = {}

# Pydantic model for heartbeat
class HeartbeatRequest(BaseModel):
    session_id: str
    is_chatbot_open: bool


@app.get("/client/stats/daily", response_model=StatsResponse)
async def get_daily_stats(client_id: str = Depends(get_client_from_header)):
    """Get daily statistics for the last 7 days"""
    conn = get_db()
    cursor = conn.cursor()

    # Calculate date range for last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=6)

    # Query to get daily stats
    query = """
        SELECT
            DATE(created_at) as date,
            COUNT(DISTINCT session_id) as visitors,
            COUNT(*) as chats
        FROM chats
        WHERE client_id = ?
            AND DATE(created_at) >= DATE(?)
            AND DATE(created_at) <= DATE(?)
        GROUP BY DATE(created_at)
        ORDER BY date ASC
    """

    cursor.execute(
        query,
        (client_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    )
    results = cursor.fetchall()

    # Create a dictionary for easy lookup
    stats_dict = {}
    for row in results:
        stats_dict[row["date"]] = {
            "date": row["date"],
            "visitors": row["visitors"],
            "chats": row["chats"]
        }

    # Fill in missing dates with zeros
    daily_stats = []
    current_date = start_date

    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')

        if date_str in stats_dict:
            daily_stats.append(stats_dict[date_str])
        else:
            daily_stats.append({
                "date": date_str,
                "visitors": 0,
                "chats": 0
            })

        current_date += timedelta(days=1)

    conn.close()

    print(f"📊 Daily stats for {client_id}: {daily_stats}")

    return {"daily_stats": daily_stats}

@app.get("/client/stats/dashboard")
async def get_dashboard_stats(client_id: str = Depends(get_client_from_header)):
    """Get all dashboard statistics in one call"""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Total Sessions (all time)
    cursor.execute(
        "SELECT COUNT(DISTINCT session_id) as total FROM chats WHERE client_id=?",
        (client_id,)
    )
    total_sessions = cursor.fetchone()["total"]

    # 2. Today's Sessions (unique sessions today)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        """
        SELECT COUNT(DISTINCT session_id) as today_sessions
        FROM chats
        WHERE client_id=? AND created_at >= ?
        """,
        (client_id, today_start)
    )
    today_sessions = cursor.fetchone()["today_sessions"]

    # 3. Today's Visitors (same as today's sessions - unique users)
    today_visitors = today_sessions

    # 4. Active Users Now (from heartbeat - chatbot currently open)
    now = datetime.now()
    timeout = timedelta(seconds=45)

    with active_users_lock:
        active_now = sum(
            1 for data in active_users.values()
            if data["client_id"] == client_id and (now - data["last_seen"]) <= timeout
        )

    conn.close()

    print(f"📊 Dashboard stats for {client_id}: Total={total_sessions}, Today={today_sessions}, Active={active_now}")

    return {
        "total_sessions": total_sessions,
        "today_sessions": today_sessions,
        "today_visitors": today_visitors,
        "active_users_now": active_now
    }


# Background cleanup task - ADD THIS AT THE END OF YOUR FILE (REPLACE EXISTING)
def cleanup_stale_users():
    """Background thread to clean up stale users"""
    while True:
        time.sleep(30)
        now = datetime.now()
        timeout = timedelta(seconds=45)

        with active_users_lock:
            stale_keys = [
                key for key, data in active_users.items()
                if (now - data["last_seen"]) > timeout
            ]

            for key in stale_keys:
                print(f"🧹 Cleaning stale user: {key}")
                del active_users[key]



# async def get_actual_daily_stats(cursor, client_id: str, start_date: datetime, end_date: datetime):
#     """
#     Get actual daily stats from database
#     """
#     try:
#         # Query to get daily visitor count (unique sessions) and chat count
#         query = """
#             SELECT
#                 DATE(created_at) as date,
#                 COUNT(DISTINCT session_id) as visitors,
#                 COUNT(*) as chats
#             FROM chats
#             WHERE client_id = ?
#                 AND created_at >= ?
#                 AND created_at <= ?
#             GROUP BY DATE(created_at)
#             ORDER BY date ASC
#         """

#         cursor.execute(query, (client_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
#         results = cursor.fetchall()

#         daily_stats = []
#         for row in results:
#             daily_stats.append({
#                 "date": row["date"],
#                 "visitors": row["visitors"],
#                 "chats": row["chats"]
#             })

#         # Fill in missing dates with zeros
#         return fill_missing_dates(daily_stats, start_date, end_date)

#     except Exception as e:
#         print(f"Error fetching actual stats: {e}")
#         return []

# def fill_missing_dates(stats: list, start_date: datetime, end_date: datetime):
#     """
#     Fill in missing dates with zero values
#     """
#     date_range = []
#     current_date = start_date

#     while current_date <= end_date:
#         date_range.append(current_date.strftime('%Y-%m-%d'))
#         current_date += timedelta(days=1)

#     # Create a dictionary for easy lookup
#     stats_dict = {stat["date"]: stat for stat in stats}

#     # Build complete list with all dates
#     complete_stats = []
#     for date in date_range:
#         if date in stats_dict:
#             complete_stats.append(stats_dict[date])
#         else:
#             complete_stats.append({
#                 "date": date,
#                 "visitors": 0,
#                 "chats": 0
#             })

#     return complete_stats

# def generate_sample_data():
#     """
#     Generate sample data for demonstration
#     """
#     stats = []
#     today = datetime.now()

#     for i in range(6, -1, -1):
#         date = today - timedelta(days=i)

#         # More realistic data pattern (higher on weekdays, lower on weekends)
#         is_weekend = date.weekday() >= 5  # 5=Saturday, 6=Sunday
#         base_visitors = 15 if is_weekend else 25
#         base_chats = 8 if is_weekend else 15

#         stats.append({
#             "date": date.strftime('%Y-%m-%d'),
#             "visitors": max(0, base_visitors + random.randint(-8, 8)),
#             "chats": max(0, base_chats + random.randint(-5, 5))
#         })

#     return stats


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


# ===== NEW ENDPOINTS =====

@app.post("/client/heartbeat/{client_id}")
async def chatbot_heartbeat(
    client_id: str,
    req: HeartbeatRequest,
    request: Request,
    x_chatbot_key: str = Header(None)
):
    """
    Track active chatbot users with heartbeat mechanism
    """
    # Validate client + chatbot_key
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE client_id=? AND chatbot_key=?", (client_id, x_chatbot_key))
    client = cursor.fetchone()
    conn.close()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # Create unique key for this user
    user_key = f"{client_id}:{req.session_id}"

    if req.is_chatbot_open:
        # User has chatbot open - update/add to active users
        active_users[user_key] = {
            "client_id": client_id,
            "session_id": req.session_id,
            "last_seen": datetime.now(),
            "ip": request.client.host,
            "user_agent": request.headers.get("user-agent", "unknown")
        }
    else:
        # User closed chatbot - remove from active users
        if user_key in active_users:
            del active_users[user_key]

    return {"status": "ok", "active": req.is_chatbot_open}


@app.get("/client/active-users/me")
async def get_active_users(client_id: str = Depends(get_client_from_header)):
    """
    Get count of currently active users for this client
    """
    now = datetime.now()
    timeout = timedelta(seconds=30)  # Consider inactive after 30 seconds without heartbeat

    # Clean up stale entries
    stale_keys = [
        key for key, data in active_users.items()
        if (now - data["last_seen"]) > timeout or data["client_id"] != client_id
    ]
    for key in stale_keys:
        del active_users[key]

    # Count active users for this client
    active_count = sum(1 for data in active_users.values() if data["client_id"] == client_id)

    # Get detailed info
    active_sessions = [
        {
            "session_id": data["session_id"],
            "last_seen": data["last_seen"].isoformat(),
            "ip": data["ip"],
            "user_agent": data["user_agent"]
        }
        for key, data in active_users.items()
        if data["client_id"] == client_id
    ]

    return {
        "active_users": active_count,
        "sessions": active_sessions
    }


# Background task to clean up stale active users
# @app.on_event("startup")
# async def startup_event():
#     # Start background cleanup thread
#     cleanup_thread = threading.Thread(target=cleanup_stale_users, daemon=True)
#     cleanup_thread.start()
#     print("✅ Active users cleanup thread started")

#     # Keep existing cleanup task
#     async def cleanup_stale_users_async():
#         while True:
#             await asyncio.sleep(60)
#             now = datetime.now()
#             timeout = timedelta(seconds=45)

#             with active_users_lock:
#                 stale_keys = [
#                     key for key, data in active_users.items()
#                     if (now - data["last_seen"]) > timeout
#                 ]
#                 for key in stale_keys:
#                     del active_users[key]

#     asyncio.create_task(cleanup_stale_users_async())


# @app.post("/client/client-reply/{session_id}")
# async def admin_reply(
#     session_id: str,
#     req: AdminReplyRequest,
#     client_id: str = Depends(get_client_from_header)
# ):
#     """Admin sends a manual reply to override chatbot"""
#     conn = get_db()
#     cursor = conn.cursor()

#     try:
#         # First, find the last assistant message ID
#         cursor.execute("""
#             SELECT id FROM chats
#             WHERE client_id=? AND session_id=? AND role='assistant' AND is_active=1
#             ORDER BY created_at DESC LIMIT 1
#         """, (client_id, session_id))

#         last_assistant = cursor.fetchone()

#         # Mark it as inactive if it exists
#         updated_rows = 0
#         if last_assistant:
#             cursor.execute("""
#                 UPDATE chats
#                 SET is_active = 0
#                 WHERE id = ?
#             """, (last_assistant['id'],))
#             updated_rows = cursor.rowcount

#         print(f"✅ Marked {updated_rows} previous assistant messages as inactive")

#         # Insert admin's override message
#         cursor.execute("""
#             INSERT INTO chats (client_id, session_id, role, message, admin_override, user_agent, is_active)
#             VALUES (?, ?, 'assistant', ?, 1, 'admin-override', 1)
#         """, (client_id, session_id, req.message))

#         conn.commit()
#         print(f"✅ Admin reply inserted successfully for session {session_id}")

#         return {
#             "success": True,
#             "message": "Admin reply sent successfully",
#             "previous_messages_deactivated": updated_rows
#         }

#     except Exception as e:
#         conn.rollback()
#         print(f"❌ Failed to send admin reply: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to send admin reply: {str(e)}"
#         )
#     finally:
#         conn.close()

@app.post("/client/client-reply/{session_id}")
async def admin_reply(
    session_id: str,
    req: AdminReplyRequest,
    client_id: str = Depends(get_client_from_header)
):
    """Admin sends a manual reply to override chatbot"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # DON'T mark previous messages as inactive - just insert the admin reply
        # The admin_override flag will distinguish it from bot messages
        # If you want to replace the last bot message, uncomment below:

        # cursor.execute("""
        #     SELECT id FROM chats
        #     WHERE client_id=? AND session_id=? AND role='assistant'
        #     AND admin_override=0 AND is_active=1
        #     ORDER BY created_at DESC LIMIT 1
        # """, (client_id, session_id))
        #
        # last_bot_message = cursor.fetchone()
        # if last_bot_message:
        #     cursor.execute("""
        #         UPDATE chats SET is_active = 0 WHERE id = ?
        #     """, (last_bot_message['id'],))

        print(f"✅ Inserting admin override message")

        # Insert admin's override message
        cursor.execute("""
            INSERT INTO chats (client_id, session_id, role, message, admin_override, user_agent, is_active)
            VALUES (?, ?, 'assistant', ?, 1, 'admin-override', 1)
        """, (client_id, session_id, req.message))

        conn.commit()
        print(f"✅ Admin reply inserted successfully for session {session_id}")

        return {
            "success": True,
            "message": "Admin reply sent successfully"
        }

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to send admin reply: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send admin reply: {str(e)}"
        )
    finally:
        conn.close()
@app.get("/client/session-details/{session_id}")
async def get_session_details(
    session_id: str,
    client_id: str = Depends(get_client_from_header)
):
    """Get full session details including user info and chat history"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Get all active chats for this session
        cursor.execute("""
            SELECT id, role, message, created_at, admin_override, country_code, user_agent
            FROM chats
            WHERE client_id=? AND session_id=? AND is_active=1
            ORDER BY created_at ASC
        """, (client_id, session_id))

        chats = [dict(row) for row in cursor.fetchall()]

        # Get session metadata (first message info)
        cursor.execute("""
            SELECT country_code, user_agent, MIN(created_at) as started_at
            FROM chats
            WHERE client_id=? AND session_id=?
            GROUP BY session_id
        """, (client_id, session_id))

        session_info = cursor.fetchone()

        return {
            "session_id": session_id,
            "chats": chats,
            "session_info": dict(session_info) if session_info else {},
            "total_messages": len(chats)
        }

    finally:
        conn.close()


@app.get("/client/active-sessions/me")
async def get_active_sessions(client_id: str = Depends(get_client_from_header)):
    """Get sessions that have recent activity (last 24 hours)"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                session_id,
                MAX(created_at) as last_activity,
                COUNT(*) as message_count,
                MAX(CASE WHEN role='user' THEN message END) as last_user_message,
                country_code,
                user_agent
            FROM chats
            WHERE client_id=?
                AND created_at >= datetime('now', '-24 hours')
                AND is_active=1
            GROUP BY session_id
            ORDER BY last_activity DESC
        """, (client_id,))

        sessions = [dict(row) for row in cursor.fetchall()]

        return {"active_sessions": sessions, "count": len(sessions)}

    finally:
        conn.close()


@app.delete("/client/delete-chat/{chat_id}")
async def delete_chat_message(
    chat_id: int,
    client_id: str = Depends(get_client_from_header)
):
    """Soft delete a specific chat message"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Verify ownership and mark as inactive
        cursor.execute("""
            UPDATE chats
            SET is_active = 0
            WHERE id=? AND client_id=?
        """, (chat_id, client_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Chat message not found")

        conn.commit()
        return {"success": True, "message": "Chat message deleted"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}")
    finally:
        conn.close()



@app.get("/client/chat-history/{client_id}/{session_id}")
def get_public_chat_history(
    client_id: str,
    session_id: str,
    x_chatbot_key: str = Header(None)
):
    """Public endpoint for chatbot widget to get chat history"""
    conn = get_db()
    cursor = conn.cursor()

    # Validate client + chatbot_key
    cursor.execute("SELECT * FROM users WHERE client_id=? AND chatbot_key=?", (client_id, x_chatbot_key))
    client = cursor.fetchone()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # Get all active chats for this session
    cursor.execute("""
        SELECT id, role, message, created_at, admin_override, country_code, user_agent
        FROM chats
        WHERE client_id=? AND session_id=? AND is_active=1
        ORDER BY created_at ASC
    """, (client_id, session_id))

    chats = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"chats": chats}
