# import os
# import sys
# import uuid
# import shutil
# import subprocess
# from datetime import datetime, timedelta

# from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Header, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import bcrypt
# import jwt
# import requests

# # DB helpers
# from db import get_db, remove_domain, get_client_by_domain, register_domain as db_register_domain

# # Add Chatbot/LLM path
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/llm"))
# sys.path.append(CHATBOT_LLM_DIR)
# from llm_service import chat_with_model, explain_context

# # === FastAPI App ===
# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Paths
# CLIENTS_DIR = os.path.join(BASE_DIR, "client_data")
# CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))
# os.makedirs(CLIENTS_DIR, exist_ok=True)

# # JWT settings
# SECRET_KEY = "your_super_secret_key"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# def create_jwt(client_id: str):
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     payload = {"client_id": client_id, "exp": expire}
#     return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# def verify_jwt(token: str):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         return payload["client_id"]
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")

# def get_client_from_header(x_token: str = Header(None)):
#     if not x_token:
#         raise HTTPException(status_code=401, detail="Missing token")
#     return verify_jwt(x_token)

# # ----------------------------
# # Models
# # ----------------------------
# class ChatRequest(BaseModel):
#     session_id: str | None = None
#     message: str

# class CrawlRequest(BaseModel):
#     # client_id: str
#     allowed_domain: str
#     start_url: str

# class SignupRequest(BaseModel):
#     name: str
#     username: str
#     password: str
#     mobile: str
#     email: str

# class LoginRequest(BaseModel):
#     username: str
#     password: str

# # ----------------------------
# # AUTH
# # ----------------------------
# @app.post("/auth/signup")
# def signup(req: SignupRequest):
#     conn = get_db()
#     cursor = conn.cursor()
#     client_id = f"{req.username}_{uuid.uuid4().hex[:6]}"
#     hashed_password = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
#     try:
#         cursor.execute("""
#             INSERT INTO users (username, password, name, email, mobile, client_id)
#             VALUES (?, ?, ?, ?, ?, ?)
#         """, (req.username, hashed_password, req.name, req.email, req.mobile, client_id))
#         conn.commit()
#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")
#     finally:
#         conn.close()
#     token = create_jwt(client_id)
#     return {"success": True, "token": token, "client_id": client_id, "message": "Signup successful"}

# @app.post("/auth/login")
# def login(req: LoginRequest):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM users WHERE username=?", (req.username,))
#     user = cursor.fetchone()
#     conn.close()
#     if not user:
#         raise HTTPException(status_code=401, detail="Invalid username or password")
#     stored_password = user["password"]
#     if isinstance(stored_password, bytes):
#         stored_password = stored_password.decode()
#     if not bcrypt.checkpw(req.password.encode(), stored_password.encode()):
#         raise HTTPException(status_code=401, detail="Invalid username or password")
#     token = create_jwt(user["client_id"])
#     return {"success": True, "token": token, "client_id": user["client_id"], "message": "Login successful"}

# @app.get("/auth/me")
# def get_me(client_id: str = Depends(get_client_from_header)):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT name, username, email FROM users WHERE client_id=?", (client_id,))
#     row = cursor.fetchone()
#     conn.close()
#     if not row:
#         raise HTTPException(status_code=404, detail="Client not found")
#     return {"client_id": client_id, "name": row["name"], "username": row["username"], "email": row["email"]}

# # ----------------------------
# # CLIENT CHAT
# # ----------------------------
# @app.post("/client/chat/me")
# def chat(req: ChatRequest, client_id: str = Depends(get_client_from_header), request: Request = None):
#     session_id = req.session_id or str(uuid.uuid4())
#     user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"
#     user_ip = request.client.host if request else "0.0.0.0"
#     try:
#         loc_resp = requests.get(f"https://ipinfo.io/{user_ip}/json", timeout=3)
#         loc_resp.raise_for_status()
#         country_code = loc_resp.json().get("country", "Unknown")
#     except Exception:
#         country_code = "Unknown"
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("""
#         INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code)
#         VALUES (?, ?, ?, ?, ?, ?)
#     """, (client_id, session_id, "user", req.message, user_agent, country_code))
#     conn.commit()
#     reply = chat_with_model(client_id, req.message)
#     cursor.execute("""
#         INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code)
#         VALUES (?, ?, ?, ?, ?, ?)
#     """, (client_id, session_id, "assistant", reply, user_agent, country_code))
#     conn.commit()
#     conn.close()
#     return {"session_id": session_id, "reply": reply, "country_code": country_code}

# @app.get("/client/chats/me")
# def get_chats(session_id: str, client_id: str = Depends(get_client_from_header)):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT session_id, role, message, user_agent, country_code, created_at
#         FROM chats
#         WHERE client_id=? AND session_id=?
#         ORDER BY created_at ASC
#     """, (client_id, session_id))
#     chats = [dict(row) for row in cursor.fetchall()]
#     conn.close()
#     return {"chats": chats}

# @app.post("/client/context/me")
# def context(req: ChatRequest, client_id: str = Depends(get_client_from_header)):
#     ctx = explain_context(client_id, req.message)
#     return {"context": ctx or "No relevant context found."}

# # ----------------------------
# # DOMAIN MANAGEMENT
# # ----------------------------
# @app.get("/client/domains/me")
# def get_domains(client_id: str = Depends(get_client_from_header)):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT domain, created_at FROM domain_mappings WHERE client_id=? ORDER BY created_at DESC", (client_id,))
#     domains = [dict(row) for row in cursor.fetchall()]
#     conn.close()
#     return {"domains": domains}

# @app.post("/client/register-my-domains/me")
# def register_domains(domains: list[str], client_id: str = Depends(get_client_from_header)):
#     registered, failed = [], []
#     for d in domains:
#         if db_register_domain(d, client_id):
#             clean = d.lower().replace("https://","").replace("http://","").replace("www.","").rstrip("/")
#             registered.append(clean)
#         else:
#             failed.append(d)
#     return {"success": len(failed)==0, "registered_domains": registered, "failed_domains": failed}

# @app.delete("/client/domains/me/{domain}")
# def delete_domain(domain: str, client_id: str = Depends(get_client_from_header)):
#     if not remove_domain(domain, client_id):
#         raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
#     return {"success": True, "message": f"Domain '{domain}' deleted"}

# # ----------------------------
# # CLIENT MANAGEMENT
# # ----------------------------
# @app.get("/admin/clients")
# def list_clients():
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT client_id, username, name, email FROM users")
#     users = [dict(row) for row in cursor.fetchall()]
#     conn.close()
#     return {"clients": users}

# @app.get("/client/me")
# def get_client(client_id: str = Depends(get_client_from_header)):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT name, username, email FROM users WHERE client_id=?", (client_id,))
#     row = cursor.fetchone()
#     conn.close()
#     if not row:
#         raise HTTPException(status_code=404, detail="Client not found")
#     return {"name": row["name"], "username": row["username"], "email": row["email"]}

# # ----------------------------
# # CHAT HISTORY
# # ----------------------------
# @app.get("/client/sessions/me")
# def get_sessions(client_id: str = Depends(get_client_from_header)):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT DISTINCT session_id FROM chats WHERE client_id=? ORDER BY created_at DESC", (client_id,))
#     sessions = [row["session_id"] for row in cursor.fetchall()]
#     conn.close()
#     return {"sessions": sessions}

# # ----------------------------
# # CRAWL, QA, EMBEDDINGS
# # ----------------------------

# @app.post("/client/me/crawl-and-embed")
# def crawl_and_embed(req: CrawlRequest, client_id: str = Depends(get_client_from_header)):
#     try:
#         # Step 1: Create client directory
#         client_dir = os.path.join(CLIENTS_DIR, client_id)
#         os.makedirs(client_dir, exist_ok=True)

#         # Step 2: Crawl website
#         output_file = os.path.join(client_dir, "website_content.json")
#         subprocess.run([
#             "scrapy", "crawl", "website_scrap",
#             "-a", f"allowed_domain={req.allowed_domain}",
#             "-a", f"start_url={req.start_url}",
#             "-a", f"output_file={output_file}"
#         ], cwd=CRAWLER_DIR, check=True)

#         # Step 3: Run embeddings pipeline
#         script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
#         subprocess.run([sys.executable, script_path, client_id], check=True)

#         return {
#             "status": "success",
#             "message": f"Crawling and embeddings completed for {client_id}",
#             "saved_to": output_file
#         }

#     except Exception as e:
#         return {"status": "error", "message": str(e)}


# @app.post("/client/crawl")
# def crawl(req: CrawlRequest):
#     try:
#         client_dir = os.path.join(CLIENTS_DIR, req.client_id)
#         os.makedirs(client_dir, exist_ok=True)
#         output_file = os.path.join(client_dir, "website_content.json")
#         subprocess.run([
#             "scrapy", "crawl", "website_scrap",
#             "-a", f"allowed_domain={req.allowed_domain}",
#             "-a", f"start_url={req.start_url}",
#             "-a", f"output_file={output_file}"
#         ], cwd=CRAWLER_DIR, check=True)
#         return {"status": "success", "message": f"Crawling completed for {req.client_id}", "saved_to": output_file}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

# @app.post("/client/upload-qa/me")
# async def upload_qa(file: UploadFile = File(...), client_id: str = Depends(get_client_from_header)):
#     client_dir = os.path.join(CLIENTS_DIR, client_id)
#     os.makedirs(client_dir, exist_ok=True)
#     file_path = os.path.join(client_dir, "custom_qa.json")
#     with open(file_path, "wb") as f:
#         shutil.copyfileobj(file.file, f)
#     return {"status": "success", "message": f"Uploaded Q&A for {client_id}"}

# @app.post("/client/embed/me")
# def run_embeddings(client_id: str = Depends(get_client_from_header)):
#     try:
#         script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
#         subprocess.run([sys.executable, script_path, client_id], check=True)
#         return {"status": "success", "message": f"Embeddings + ingestion done for {client_id}"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

# @app.get("/client/status/me")
# def check_status(client_id: str = Depends(get_client_from_header)):
#     client_dir = os.path.join(CLIENTS_DIR, client_id)
#     return {
#         "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
#         "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
#         "embedded": True
#     }



import os
import sys
import uuid
import shutil
import subprocess
from datetime import datetime, timedelta

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt
import requests

# DB helpers
from db import get_db, remove_domain, get_client_by_domain, register_domain as db_register_domain

# JWT Authentication
from auth_utils import create_jwt, get_client_from_header

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
CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))
os.makedirs(CLIENTS_DIR, exist_ok=True)

# ----------------------------
# Models
# ----------------------------
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class CrawlRequest(BaseModel):
    # client_id: str
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

# ----------------------------
# AUTH
# ----------------------------
@app.post("/auth/signup")
def signup(req: SignupRequest):
    conn = get_db()
    cursor = conn.cursor()
    client_id = f"{req.username}_{uuid.uuid4().hex[:6]}"
    hashed_password = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    try:
        cursor.execute("""
            INSERT INTO users (username, password, name, email, mobile, client_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (req.username, hashed_password, req.name, req.email, req.mobile, client_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")
    finally:
        conn.close()
    token = create_jwt(client_id)
    return {"success": True, "token": token, "client_id": client_id, "message": "Signup successful"}

@app.post("/auth/login")
def login(req: LoginRequest):
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
def get_me(client_id: str = Depends(get_client_from_header)):
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
@app.post("/client/chat/me")
def chat(req: ChatRequest, client_id: str = Depends(get_client_from_header), request: Request = None):
    session_id = req.session_id or str(uuid.uuid4())
    user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"
    user_ip = request.client.host if request else "0.0.0.0"
    try:
        loc_resp = requests.get(f"https://ipinfo.io/{user_ip}/json", timeout=3)
        loc_resp.raise_for_status()
        country_code = loc_resp.json().get("country", "Unknown")
    except Exception:
        country_code = "Unknown"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_id, session_id, "user", req.message, user_agent, country_code))
    conn.commit()
    reply = chat_with_model(client_id, req.message)
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_id, session_id, "assistant", reply, user_agent, country_code))
    conn.commit()
    conn.close()
    return {"session_id": session_id, "reply": reply, "country_code": country_code}

@app.get("/client/chats/me")
def get_chats(session_id: str, client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, role, message, user_agent, country_code, created_at
        FROM chats
        WHERE client_id=? AND session_id=?
        ORDER BY created_at ASC
    """, (client_id, session_id))
    chats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"chats": chats}

@app.post("/client/context/me")
def context(req: ChatRequest, client_id: str = Depends(get_client_from_header)):
    ctx = explain_context(client_id, req.message)
    return {"context": ctx or "No relevant context found."}

# ----------------------------
# DOMAIN MANAGEMENT
# ----------------------------
@app.get("/client/domains/me")
def get_domains(client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT domain, created_at FROM domain_mappings WHERE client_id=? ORDER BY created_at DESC", (client_id,))
    domains = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"domains": domains}

@app.post("/client/register-my-domains/me")
def register_domains(domains: list[str], client_id: str = Depends(get_client_from_header)):
    registered, failed = [], []
    for d in domains:
        if db_register_domain(d, client_id):
            clean = d.lower().replace("https://","").replace("http://","").replace("www.","").rstrip("/")
            registered.append(clean)
        else:
            failed.append(d)
    return {"success": len(failed)==0, "registered_domains": registered, "failed_domains": failed}

@app.delete("/client/domains/me/{domain}")
def delete_domain(domain: str, client_id: str = Depends(get_client_from_header)):
    if not remove_domain(domain, client_id):
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
    return {"success": True, "message": f"Domain '{domain}' deleted"}

# ----------------------------
# CLIENT MANAGEMENT
# ----------------------------
@app.get("/admin/clients")
def list_clients():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT client_id, username, name, email FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"clients": users}

@app.get("/client/me")
def get_client(client_id: str = Depends(get_client_from_header)):
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
def get_sessions(client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM chats WHERE client_id=? ORDER BY created_at DESC", (client_id,))
    sessions = [row["session_id"] for row in cursor.fetchall()]
    conn.close()
    return {"sessions": sessions}

# ----------------------------
# CRAWL, QA, EMBEDDINGS
# ----------------------------

@app.post("/client/me/crawl-and-embed")
def crawl_and_embed(req: CrawlRequest, client_id: str = Depends(get_client_from_header)):
    try:
        # Step 1: Create client directory
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        os.makedirs(client_dir, exist_ok=True)

        # Step 2: Crawl website
        output_file = os.path.join(client_dir, "website_content.json")
        subprocess.run([
            "scrapy", "crawl", "website_scrap",
            "-a", f"allowed_domain={req.allowed_domain}",
            "-a", f"start_url={req.start_url}",
            "-a", f"output_file={output_file}"
        ], cwd=CRAWLER_DIR, check=True)

        # Step 3: Run embeddings pipeline
        script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
        subprocess.run([sys.executable, script_path, client_id], check=True)

        return {
            "status": "success",
            "message": f"Crawling and embeddings completed for {client_id}",
            "saved_to": output_file
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/client/crawl")
def crawl(req: CrawlRequest):
    try:
        client_dir = os.path.join(CLIENTS_DIR, req.client_id)
        os.makedirs(client_dir, exist_ok=True)
        output_file = os.path.join(client_dir, "website_content.json")
        subprocess.run([
            "scrapy", "crawl", "website_scrap",
            "-a", f"allowed_domain={req.allowed_domain}",
            "-a", f"start_url={req.start_url}",
            "-a", f"output_file={output_file}"
        ], cwd=CRAWLER_DIR, check=True)
        return {"status": "success", "message": f"Crawling completed for {req.client_id}", "saved_to": output_file}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/client/upload-qa/me")
async def upload_qa(file: UploadFile = File(...), client_id: str = Depends(get_client_from_header)):
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_dir, exist_ok=True)
    file_path = os.path.join(client_dir, "custom_qa.json")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": "success", "message": f"Uploaded Q&A for {client_id}"}

@app.post("/client/embed/me")
def run_embeddings(client_id: str = Depends(get_client_from_header)):
    try:
        script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
        subprocess.run([sys.executable, script_path, client_id], check=True)
        return {"status": "success", "message": f"Embeddings + ingestion done for {client_id}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/client/status/me")
def check_status(client_id: str = Depends(get_client_from_header)):
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    return {
        "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
        "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
        "embedded": True
    }