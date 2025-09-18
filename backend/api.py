import os
import sys
import uuid
import shutil
import subprocess
import sqlite3
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Header
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from db import get_db

# Add Chatbot/llm to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/llm"))
sys.path.append(CHATBOT_LLM_DIR)

from llm_service import chat_with_model, explain_context

# === FastAPI App ===
app = FastAPI()

# Allow frontend (React) to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174","http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Paths ===
CLIENTS_DIR = os.path.join(BASE_DIR, "client_data")
CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))
os.makedirs(CLIENTS_DIR, exist_ok=True)

# ----------------------------
# 🔹 Models
# ----------------------------
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class CrawlRequest(BaseModel):
    client_id: str
    allowed_domain: str
    start_url: str

class ClientRequest(BaseModel):
    client_id: str

class SignupRequest(BaseModel):
    name: str
    username: str
    password: str
    mobile: str
    email: str

class LoginRequest(BaseModel):
    username: str
    password: str


import requests
from fastapi import Request

@app.post("/client/chat/{client_id}")
def client_chat(client_id: str, req: ChatRequest, request: Request, x_chatbot_key: str = Header(None)):
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


    # ✅ Store user message and country code
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

    conn.close()

    return {"session_id": session_id, "reply": bot_reply}




# ----------------------------
# 🔹 CHAT CONTEXT
# ----------------------------
@app.post("/client/context/{client_id}")
def context_endpoint(client_id: str, req: ChatRequest, x_chatbot_key: str = Header(None)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE client_id=? AND chatbot_key=?", (client_id, x_chatbot_key))
    client = cursor.fetchone()
    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    ctx = explain_context(client_id, req.message)
    return {"context": ctx or "No relevant context found."}

# ----------------------------
# 🔹 ADMIN ENDPOINTS
# ----------------------------
@app.post("/client/crawl")
def crawl(req: CrawlRequest):
    try:
        client_dir = os.path.join(CLIENTS_DIR, req.client_id)
        os.makedirs(client_dir, exist_ok=True)

        output_file = os.path.join(client_dir, "website_content.json")

        subprocess.run(
            [
                "scrapy", "crawl", "website_scrap",
                "-a", f"allowed_domain={req.allowed_domain}",
                "-a", f"start_url={req.start_url}",
                "-a", f"output_file={output_file}"
            ],
            cwd=CRAWLER_DIR,
            check=True
        )

        return {
            "status": "success",
            "message": f"Crawling completed for {req.client_id}",
            "saved_to": output_file
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/client/upload-qa/{client_id}")
async def upload_qa(client_id: str, file: UploadFile = File(...)):
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_dir, exist_ok=True)

    file_path = os.path.join(client_dir, "custom_qa.json")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"status": "success", "message": f"Uploaded Q&A for {client_id}"}

@app.post("/client/embed/{client_id}")
def run_embeddings(client_id: str):
    try:
        script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
        subprocess.run([sys.executable, script_path, client_id], check=True)
        return {"status": "success", "message": f"Embeddings + ingestion done for {client_id}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/client/status/{client_id}")
def check_status(client_id: str):
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    if not os.path.exists(client_dir):
        return {"status": "not_found"}

    return {
        "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
        "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
        "embedded": True  # ✅ global Chroma DB assumed
    }

# ----------------------------
# 🔹 AUTH (Signup + Login)
# ----------------------------
import bcrypt
from fastapi import HTTPException
import uuid

@app.post("/auth/signup")
def signup(req: SignupRequest):
    conn = get_db()
    cursor = conn.cursor()
    client_id = f"{req.username}_{uuid.uuid4().hex[:6]}"
    chatbot_key = uuid.uuid4().hex  # ✅ generate API key

    # Hash the password before storing it
    hashed_password = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt())

    try:
        cursor.execute("""
            INSERT INTO users (username, password, name, email, mobile, client_id, chatbot_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (req.username, hashed_password.decode('utf-8'), req.name, req.email, req.mobile, client_id, chatbot_key))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")
    finally:
        conn.close()

    return {"success": True, "client_id": client_id, "chatbot_key": chatbot_key, "message": "Signup successful"}

@app.post("/auth/login")
def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()

    try:
        print(f"Login attempt for username: '{req.username}'")
        print(f"Login attempt for password: '{req.password}'")

        cursor.execute("SELECT * FROM users WHERE username=?", (req.username,))
        user = cursor.fetchone()

        # print(f"User found in database: {user is not None}")

        if not user:
            # print("User not found - raising 401")
            raise HTTPException(status_code=401, detail="Invalid username or password")

        stored_password = user['password']
        # print(f"Stored password: '{stored_password}'")
        # print(f"Stored password type: {type(stored_password)}")
        # print(f"Stored password length: {len(stored_password)}")

        # Convert bytes to string if needed
        if isinstance(stored_password, bytes):
            stored_password = stored_password.decode('utf-8')
            # print(f"Converted to string: '{stored_password}'")

        # print(f"Password starts with bcrypt prefix: {stored_password.startswith(('$2a$', '$2b$', '$2y$'))}")

        # Check if password is hashed (bcrypt hashes start with $2a$, $2b$, or $2y$)
        if stored_password.startswith(('$2a$', '$2b$', '$2y$')):
            print("Using bcrypt verification")
            # It's a hashed password - use bcrypt
            stored_password_bytes = stored_password.encode('utf-8')
            password_match = bcrypt.checkpw(req.password.encode('utf-8'), stored_password_bytes)
            # print(f"Bcrypt password match: {password_match}")

            if not password_match:
                # print("Bcrypt verification failed - raising 401")
                raise HTTPException(status_code=401, detail="Invalid username or password")
        else:
            # print("Using plain text comparison")
            # It's a plain text password - direct comparison
            password_match = req.password == stored_password
            # print(f"Plain text password match: {password_match}")

            if not password_match:
                # print("Plain text verification failed - raising 401")
                raise HTTPException(status_code=401, detail="Invalid username or password")

        # print("Login successful - returning success response")
        return {
            "success": True,
            "client_id": user["client_id"],
            "chatbot_key": user["chatbot_key"],
            "message": "Login successful"
        }

    except HTTPException as http_exc:
        # print(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # print(f"Unexpected login error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.close()

# Add these imports at the top of your main.py
from db import get_client_by_domain, register_domain as db_register_domain

# Add these endpoints to your main.py file

@app.get("/client/lookup-by-domain")
def lookup_client_by_domain(domain: str):
    """Lookup client_id and chatbot_key by domain"""
    try:
        result = get_client_by_domain(domain)

        if not result:
            raise HTTPException(status_code=404, detail="Domain not found")

        return {
            "client_id": result["client_id"],
            "chatbot_key": result["chatbot_key"],
            "client_name": result["client_name"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")

@app.get("/client/{client_id}/domains")
def get_client_domains(client_id: str, x_chatbot_key: str = Header(None)):
    """Get all domains registered for a specific client"""
    conn = get_db()
    cursor = conn.cursor()

    # Verify client + chatbot_key
    cursor.execute("SELECT * FROM users WHERE client_id=? AND chatbot_key=?", (client_id, x_chatbot_key))
    client = cursor.fetchone()
    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    try:
        cursor.execute("""
            SELECT domain, created_at
            FROM domain_mappings
            WHERE client_id = ?
            ORDER BY created_at DESC
        """, (client_id,))

        domains = [dict(row) for row in cursor.fetchall()]

        return {"domains": domains}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch domains: {str(e)}")
    finally:
        conn.close()

@app.post("/client/register-my-domains/{client_id}")
def register_client_domains(client_id: str, domains: list[str], x_chatbot_key: str = Header(None)):
    """Allow a client to register their own domains"""
    conn = get_db()
    cursor = conn.cursor()

    # Verify client + chatbot_key
    cursor.execute("SELECT * FROM users WHERE client_id=? AND chatbot_key=?", (client_id, x_chatbot_key))
    client = cursor.fetchone()
    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")
    conn.close()

    registered_domains = []
    failed_domains = []

    for domain in domains:
        success = db_register_domain(domain, client_id)
        if success:
            clean_domain = domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')
            registered_domains.append(clean_domain)
        else:
            failed_domains.append(domain)

    return {
        "success": len(failed_domains) == 0,
        "registered_domains": registered_domains,
        "failed_domains": failed_domains,
        "message": f"Successfully registered {len(registered_domains)} domain(s)"
    }




# ----------------------------
# 🔹 CLIENT MANAGEMENT
# ----------------------------
@app.get("/admin/clients")
def list_clients():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT client_id, username, name, email FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    return {"clients": users}

@app.get("/client/{client_id}")
def get_client(client_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, username, email FROM users WHERE client_id = ?", (client_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return {
        "name": row["name"],
        "username": row["username"],
        "email": row["email"],
    }


# ----------------------------
# 🔹 CHAT HISTORY ENDPOINTS
# ----------------------------
@app.get("/client/{client_id}/sessions")
def get_sessions(client_id: str):
    """Return all unique session IDs for a client"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM chats WHERE client_id=? ORDER BY created_at DESC", (client_id,))
    sessions = [row["session_id"] for row in cursor.fetchall()]
    conn.close()
    return {"sessions": sessions}


@app.get("/client/{client_id}/chats")
def get_chats(client_id: str, session_id: str):
    """Return all chat messages for a given client + session"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_id, role, message, user_agent, created_at, country_code FROM chats WHERE client_id=? AND session_id=? ORDER BY created_at ASC",
        (client_id, session_id)
    )
    chats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"chats": chats}
