# # import sys
# # import os
# # from fastapi import FastAPI
# # from pydantic import BaseModel
# # from fastapi.middleware.cors import CORSMiddleware

# # # Ensure parent directory is in Python path
# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# # from Chatbot.llm.llm import chat_with_model, retrieve_context

# # app = FastAPI()

# # # Allow frontend (React) to call API
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["http://localhost:5173"],  
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # class ChatRequest(BaseModel):
# #     message: str

# # @app.post("/chat")
# # def chat_endpoint(req: ChatRequest):
# #     answer = chat_with_model(req.message)
# #     return {"reply": answer}

# # @app.post("/context")
# # def context_endpoint(req: ChatRequest):
# #     context = retrieve_context(req.message)
# #     return {"context": context or "No relevant context found."}


# # import os
# # import sys
# # import shutil
# # import subprocess
# # from fastapi import FastAPI, UploadFile, File
# # from pydantic import BaseModel
# # from fastapi.middleware.cors import CORSMiddleware

# # # Add parent dir to path
# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# # from Chatbot.llm.llm import chat_with_model, retrieve_context

# # # === FastAPI App ===
# # app = FastAPI()

# # # Allow frontend (React) to call API
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["http://localhost:5173"],  
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # # === Paths ===
# # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # CLIENTS_DIR = os.path.join(BASE_DIR, "client_data")
# # CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))

# # os.makedirs(CLIENTS_DIR, exist_ok=True)

# # # ----------------------------
# # # 🔹 Models
# # # ----------------------------
# # class ChatRequest(BaseModel):
# #     message: str
# #     client_id: str

# # class CrawlRequest(BaseModel):
# #     client_id: str
# #     allowed_domain: str
# #     start_url: str

# # class ClientRequest(BaseModel):
# #     client_id: str

# # # ----------------------------
# # # 🔹 CHAT ENDPOINTS
# # # ----------------------------
# # @app.post("/chat")
# # def chat_endpoint(req: ChatRequest):
# #     answer = chat_with_model(req.message, req.client_id)
# #     return {"reply": answer}

# # @app.post("/context")
# # def context_endpoint(req: ChatRequest):
# #     context = retrieve_context(req.message, req.client_id)
# #     return {"context": context or "No relevant context found."}

# # # ----------------------------
# # # 🔹 ADMIN ENDPOINTS
# # # ----------------------------
# # @app.post("/admin/crawl")
# # def crawl(req: CrawlRequest):
# #     try:
# #         client_dir = os.path.join(CLIENTS_DIR, req.client_id)
# #         os.makedirs(client_dir, exist_ok=True)

# #         output_file = os.path.join(client_dir, "website_content.json")

# #         subprocess.run(
# #             [
# #                 "scrapy", "crawl", "website_scrap",
# #                 "-a", f"allowed_domain={req.allowed_domain}",
# #                 "-a", f"start_url={req.start_url}",
# #                 "-a", f"output_file={output_file}"
# #             ],
# #             cwd=CRAWLER_DIR,
# #             check=True
# #         )

# #         return {
# #             "status": "success",
# #             "message": f"Crawling completed for {req.client_id}",
# #             "saved_to": output_file
# #         }
# #     except Exception as e:
# #         return {"status": "error", "message": str(e)}

# # @app.post("/admin/upload-qa/{client_id}")
# # async def upload_qa(client_id: str, file: UploadFile = File(...)):
# #     """Upload custom Q&A JSON for a client."""
# #     client_dir = os.path.join(CLIENTS_DIR, client_id)
# #     os.makedirs(client_dir, exist_ok=True)

# #     file_path = os.path.join(client_dir, "custom_qa.json")
# #     with open(file_path, "wb") as f:
# #         shutil.copyfileobj(file.file, f)

# #     return {"status": "success", "message": f"Uploaded Q&A for {client_id}"}

# # @app.post("/admin/embed/{client_id}")
# # def run_embeddings(client_id: str):
# #     """Run chunking + embeddings + ingest into Chroma."""
# #     try:
        
# #         script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
# #         print(script_path)
# #         subprocess.run([sys.executable, script_path, client_id], check=True)
# #         return {"status": "success", "message": f"Embeddings + ingestion done for {client_id}"}
# #     except Exception as e:
# #         return {"status": "error", "message": str(e)}

# # @app.get("/admin/status/{client_id}")
# # def check_status(client_id: str):
# #     """Check if crawl, Q&A, and embeddings exist."""
# #     client_dir = os.path.join(CLIENTS_DIR, client_id)
# #     if not os.path.exists(client_dir):
# #         return {"status": "not_found"}

# #     return {
# #         "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
# #         "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
# #         "embedded": os.path.exists(os.path.join(client_dir, "chroma_db")),
# #     }

# # # ----------------------------
# # # 🔹 CLIENT MANAGEMENT
# # # ----------------------------
# # # Temporary in-memory client storage
# # CLIENTS = []

# # @app.get("/admin/clients")
# # def list_clients():
# #     return {"clients": CLIENTS}

# # @app.post("/admin/add-client")
# # def add_client(req: ClientRequest):
# #     if req.client_id not in CLIENTS:
# #         CLIENTS.append(req.client_id)
# #     return {"message": f"Client '{req.client_id}' added.", "clients": CLIENTS}




# import os
# import sys
# import uuid
# import shutil
# import subprocess
# from fastapi import FastAPI, UploadFile, File,HTTPException
# from pydantic import BaseModel
# from fastapi.middleware.cors import CORSMiddleware
# from db import get_db

# # Add Chatbot/llm to path
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/llm"))
# sys.path.append(CHATBOT_LLM_DIR)

# from llm_service import chat_with_model, explain_context  # ✅ updated import

# # === FastAPI App ===
# app = FastAPI()

# # Allow frontend (React) to call API
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173","http://localhost:5174"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # === Paths ===
# CLIENTS_DIR = os.path.join(BASE_DIR, "client_data")
# CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))
# os.makedirs(CLIENTS_DIR, exist_ok=True)

# # ----------------------------
# # 🔹 Models
# # ----------------------------
# class ChatRequest(BaseModel):
#     client_id: str
#     message: str

# class CrawlRequest(BaseModel):
#     client_id: str
#     allowed_domain: str
#     start_url: str

# class ClientRequest(BaseModel):
#     client_id: str

# # ----------------------------
# # 🔹 CHAT ENDPOINTS
# # ----------------------------
# @app.post("/chat")
# def chat_endpoint(req: ChatRequest):
#     answer = chat_with_model(req.client_id, req.message)  # ✅ fixed order
#     return {"reply": answer}

# @app.post("/context")
# def context_endpoint(req: ChatRequest):
#     ctx = explain_context(req.client_id, req.message)  # ✅ use explain_context
#     return {"context": ctx or "No relevant context found."}

# # ----------------------------
# # 🔹 ADMIN ENDPOINTS
# # ----------------------------
# @app.post("/client/crawl")
# def crawl(req: CrawlRequest):
#     try:
#         client_dir = os.path.join(CLIENTS_DIR, req.client_id)
#         os.makedirs(client_dir, exist_ok=True)

#         output_file = os.path.join(client_dir, "website_content.json")

#         subprocess.run(
#             [
#                 "scrapy", "crawl", "website_scrap",
#                 "-a", f"allowed_domain={req.allowed_domain}",
#                 "-a", f"start_url={req.start_url}",
#                 "-a", f"output_file={output_file}"
#             ],
#             cwd=CRAWLER_DIR,
#             check=True
#         )

#         return {
#             "status": "success",
#             "message": f"Crawling completed for {req.client_id}",
#             "saved_to": output_file
#         }
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

# @app.post("/client/upload-qa/{client_id}")
# async def upload_qa(client_id: str, file: UploadFile = File(...)):
#     """Upload custom Q&A JSON for a client."""
#     client_dir = os.path.join(CLIENTS_DIR, client_id)
#     os.makedirs(client_dir, exist_ok=True)

#     file_path = os.path.join(client_dir, "custom_qa.json")
#     with open(file_path, "wb") as f:
#         shutil.copyfileobj(file.file, f)

#     return {"status": "success", "message": f"Uploaded Q&A for {client_id}"}

# @app.post("/client/embed/{client_id}")
# def run_embeddings(client_id: str):
#     """Run chunking + embeddings + ingest into Chroma."""
#     try:
#         script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
#         subprocess.run([sys.executable, script_path, client_id], check=True)
#         return {"status": "success", "message": f"Embeddings + ingestion done for {client_id}"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

# @app.get("/client/status/{client_id}")
# def check_status(client_id: str):
#     """Check if crawl, Q&A, and embeddings exist for a client."""
#     client_dir = os.path.join(CLIENTS_DIR, client_id)
#     if not os.path.exists(client_dir):
#         return {"status": "not_found"}

#     return {
#         "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
#         "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
#         # embeddings are stored in global Chroma DB, not per client folder
#         "embedded": True  # TODO: optionally check Chroma for collection existence
#     }

# # ----------------------------
# # 🔹 CLIENT MANAGEMENT
# # ----------------------------
# CLIENTS = []

# # @app.get("/admin/clients")
# # def list_clients():
# #     return {"clients": CLIENTS}

# # @app.post("/admin/add-client")
# # def add_client(req: ClientRequest):
# #     if req.client_id not in CLIENTS:
# #         CLIENTS.append(req.client_id)
# #     return {"message": f"Client '{req.client_id}' added.", "clients": CLIENTS}
    
    
    
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
# # 🔹 SIGNUP
# # ----------------------------
# @app.post("/auth/signup")
# def signup(req: SignupRequest):
#     conn = get_db()
#     cursor = conn.cursor()

#     # generate client_id = username + short uuid
#     client_id = f"{req.username}_{uuid.uuid4().hex[:6]}"

#     try:
#         cursor.execute("""
#             INSERT INTO users (username, password, name, email, mobile, client_id)
#             VALUES (?, ?, ?, ?, ?, ?)
#         """, (req.username, req.password, req.name, req.email, req.mobile, client_id))
#         conn.commit()
#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")

#     # Add to in-memory list
#     if client_id not in CLIENTS:
#         CLIENTS.append(client_id)

#     return {"success": True, "client_id": client_id, "message": "Signup successful"}


# # ----------------------------
# # 🔹 LOGIN
# # ----------------------------
# @app.post("/auth/login")
# def login(req: LoginRequest):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (req.username, req.password))
#     user = cursor.fetchone()

#     if not user:
#         raise HTTPException(status_code=401, detail="Invalid username or password")

#     client_id = user["client_id"]

#     return {
#         "success": True,
#         "client_id": client_id,
#         "message": "Login successful"
#     }


# # ----------------------------
# # 🔹 LIST CLIENTS
# # ----------------------------
# @app.get("/admin/clients")
# def list_clients():
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT client_id, username, name, email FROM users")
#     users = [dict(row) for row in cursor.fetchall()]
#     return {"clients": users}


# @app.get("/client/{client_id}")
# def get_client(client_id: str):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT name, username, email FROM users WHERE client_id = ?", (client_id,))
#     row = cursor.fetchone()
#     if not row:
#         raise HTTPException(status_code=404, detail="Client not found")
#     return {
#         "name": row["name"],
#         "username": row["username"],
#         "email": row["email"],
#     }
    
    
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
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
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

# ----------------------------
# 🔹 CLIENT CHAT (with session logging)
# ----------------------------
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

    # ✅ Capture user-agent
    user_agent = request.headers.get("user-agent", "unknown")

    # ✅ Store user message
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent)
        VALUES (?, ?, ?, ?, ?)
    """, (client_id, session_id, "user", req.message, user_agent))
    conn.commit()

    # ✅ Generate chatbot reply
    bot_reply = chat_with_model(client_id, req.message)

    # ✅ Store assistant reply
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent)
        VALUES (?, ?, ?, ?, ?)
    """, (client_id, session_id, "assistant", bot_reply, user_agent))
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
@app.post("/auth/signup")
def signup(req: SignupRequest):
    conn = get_db()
    cursor = conn.cursor()

    client_id = f"{req.username}_{uuid.uuid4().hex[:6]}"
    chatbot_key = uuid.uuid4().hex  # ✅ generate API key

    try:
        cursor.execute("""
            INSERT INTO users (username, password, name, email, mobile, client_id, chatbot_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (req.username, req.password, req.name, req.email, req.mobile, client_id, chatbot_key))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")

    return {"success": True, "client_id": client_id, "chatbot_key": chatbot_key, "message": "Signup successful"}

@app.post("/auth/login")
def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (req.username, req.password))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "success": True,
        "client_id": user["client_id"],
        "chatbot_key": user["chatbot_key"],
        "message": "Login successful"
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
        "SELECT session_id, role, message, user_agent, created_at FROM chats WHERE client_id=? AND session_id=? ORDER BY created_at ASC",
        (client_id, session_id)
    )
    chats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"chats": chats}
