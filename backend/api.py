import os
import sys
import uuid
import shutil
import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt
import requests
import aiofiles
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

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

# Thread pools for different types of operations
# Use ThreadPoolExecutor for I/O bound operations
io_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="io_worker")
# Use ProcessPoolExecutor for CPU bound operations like embeddings
process_executor = ProcessPoolExecutor(max_workers=4)

# Task status tracking
task_status: Dict[str, Dict[str, Any]] = {}

# ----------------------------
# Models
# ----------------------------
class ChatRequest(BaseModel):
    session_id: str | None = None
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
# ASYNC HELPER FUNCTIONS
# ----------------------------

async def run_subprocess_async(cmd: list, cwd: str = None) -> tuple[int, str, str]:
    """Run subprocess asynchronously"""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()

def update_task_status(task_id: str, status: str, message: str = "", progress: int = 0, result: Any = None):
    """Update task status in memory (in production, use Redis or database)"""
    task_status[task_id] = {
        "status": status,
        "message": message,
        "progress": progress,
        "result": result,
        "updated_at": datetime.now().isoformat()
    }

async def crawl_website_async(client_id: str, allowed_domain: str, start_url: str, task_id: str):
    """Asynchronous website crawling"""
    try:
        update_task_status(task_id, "running", "Starting website crawl...", 10)
        
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        os.makedirs(client_dir, exist_ok=True)
        output_file = os.path.join(client_dir, "website_content.json")
        
        cmd = [
            "scrapy", "crawl", "website_scrap",
            "-a", f"allowed_domain={allowed_domain}",
            "-a", f"start_url={start_url}",
            "-a", f"output_file={output_file}"
        ]
        
        update_task_status(task_id, "running", "Crawling website...", 50)
        
        returncode, stdout, stderr = await run_subprocess_async(cmd, CRAWLER_DIR)
        
        if returncode != 0:
            raise Exception(f"Crawling failed: {stderr}")
            
        update_task_status(task_id, "completed", "Website crawling completed successfully", 100, {
            "output_file": output_file,
            "crawled_pages": "Check logs for details"
        })
        
    except Exception as e:
        update_task_status(task_id, "failed", f"Crawling failed: {str(e)}", 0)

async def run_embeddings_async(client_id: str, task_id: str):
    """Asynchronous embeddings processing"""
    try:
        update_task_status(task_id, "running", "Starting embeddings generation...", 10)
        
        script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
        cmd = [sys.executable, script_path, client_id]
        
        update_task_status(task_id, "running", "Processing embeddings...", 50)
        
        returncode, stdout, stderr = await run_subprocess_async(cmd)
        
        if returncode != 0:
            raise Exception(f"Embeddings failed: {stderr}")
            
        update_task_status(task_id, "completed", "Embeddings generated successfully", 100, {
            "client_id": client_id,
            "embeddings": "Generated and stored"
        })
        
    except Exception as e:
        update_task_status(task_id, "failed", f"Embeddings failed: {str(e)}", 0)

async def crawl_and_embed_async(client_id: str, allowed_domain: str, start_url: str, task_id: str):
    """Combined crawl and embed operation"""
    try:
        update_task_status(task_id, "running", "Starting crawl and embed pipeline...", 5)
        
        # Step 1: Crawl
        await crawl_website_async(client_id, allowed_domain, start_url, f"{task_id}_crawl")
        update_task_status(task_id, "running", "Crawling completed, starting embeddings...", 60)
        
        # Step 2: Embeddings
        await run_embeddings_async(client_id, f"{task_id}_embed")
        
        update_task_status(task_id, "completed", "Crawl and embed pipeline completed successfully", 100, {
            "client_id": client_id,
            "domain": allowed_domain,
            "start_url": start_url
        })
        
    except Exception as e:
        update_task_status(task_id, "failed", f"Pipeline failed: {str(e)}", 0)

# ----------------------------
# AUTH (keeping original)
# ----------------------------
@app.post("/auth/signup")
async def signup(req: SignupRequest):
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
# CLIENT CHAT (with async improvements)
# ----------------------------
@app.post("/client/chat/me")
async def chat(req: ChatRequest, client_id: str = Depends(get_client_from_header), request: Request = None):
    session_id = req.session_id or str(uuid.uuid4())
    user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"
    user_ip = request.client.host if request else "0.0.0.0"
    
    # Async location lookup
    try:
        async with asyncio.timeout(3):
            loop = asyncio.get_event_loop()
            loc_resp = await loop.run_in_executor(
                io_executor, 
                lambda: requests.get(f"https://ipinfo.io/{user_ip}/json", timeout=3)
            )
            loc_resp.raise_for_status()
            country_code = loc_resp.json().get("country", "Unknown")
    except Exception:
        country_code = "Unknown"
    
    # Run chat model in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(io_executor, chat_with_model, client_id, req.message)
    
    # Database operations
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_id, session_id, "user", req.message, user_agent, country_code))
    conn.commit()
    
    cursor.execute("""
        INSERT INTO chats (client_id, session_id, role, message, user_agent, country_code)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_id, session_id, "assistant", reply, user_agent, country_code))
    conn.commit()
    conn.close()
    
    return {"session_id": session_id, "reply": reply, "country_code": country_code}

@app.get("/client/chats/me")
async def get_chats(session_id: str, client_id: str = Depends(get_client_from_header)):
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
async def context(req: ChatRequest, client_id: str = Depends(get_client_from_header)):
    loop = asyncio.get_event_loop()
    ctx = await loop.run_in_executor(io_executor, explain_context, client_id, req.message)
    return {"context": ctx or "No relevant context found."}

# ----------------------------
# DOMAIN MANAGEMENT (keeping original)
# ----------------------------
@app.get("/client/domains/me")
async def get_domains(client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT domain, created_at FROM domain_mappings WHERE client_id=? ORDER BY created_at DESC", (client_id,))
    domains = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"domains": domains}

@app.post("/client/register-my-domains/me")
async def register_domains(domains: list[str], client_id: str = Depends(get_client_from_header)):
    registered, failed = [], []
    for d in domains:
        if db_register_domain(d, client_id):
            clean = d.lower().replace("https://","").replace("http://","").replace("www.","").rstrip("/")
            registered.append(clean)
        else:
            failed.append(d)
    return {"success": len(failed)==0, "registered_domains": registered, "failed_domains": failed}

@app.delete("/client/domains/me/{domain}")
async def delete_domain(domain: str, client_id: str = Depends(get_client_from_header)):
    if not remove_domain(domain, client_id):
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
    return {"success": True, "message": f"Domain '{domain}' deleted"}

# ----------------------------
# CLIENT MANAGEMENT (keeping original)
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
# CHAT HISTORY (keeping original)
# ----------------------------
@app.get("/client/sessions/me")
async def get_sessions(client_id: str = Depends(get_client_from_header)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM chats WHERE client_id=? ORDER BY created_at DESC", (client_id,))
    sessions = [row["session_id"] for row in cursor.fetchall()]
    conn.close()
    return {"sessions": sessions}

# ----------------------------
# ASYNC CRAWL, QA, EMBEDDINGS
# ----------------------------

@app.post("/client/me/crawl-and-embed", response_model=TaskResponse)
async def crawl_and_embed(
    req: CrawlRequest, 
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_client_from_header)
):
    """Start crawl and embed process asynchronously"""
    task_id = f"crawl_embed_{client_id}_{uuid.uuid4().hex[:8]}"
    
    # Initialize task status
    update_task_status(task_id, "queued", "Task queued for processing", 0)
    
    # Add background task
    background_tasks.add_task(
        crawl_and_embed_async, 
        client_id, 
        req.allowed_domain, 
        req.start_url, 
        task_id
    )
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="Crawl and embed task has been queued. Check status using task_id."
    )

@app.post("/client/me/crawl", response_model=TaskResponse)
async def crawl_only(
    req: CrawlRequest, 
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_client_from_header)
):
    """Start crawling process asynchronously"""
    task_id = f"crawl_{client_id}_{uuid.uuid4().hex[:8]}"
    
    update_task_status(task_id, "queued", "Crawl task queued for processing", 0)
    
    background_tasks.add_task(
        crawl_website_async, 
        client_id, 
        req.allowed_domain, 
        req.start_url, 
        task_id
    )
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="Crawl task has been queued. Check status using task_id."
    )

@app.post("/client/me/embed", response_model=TaskResponse)
async def embed_only(
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_client_from_header)
):
    """Start embeddings process asynchronously"""
    task_id = f"embed_{client_id}_{uuid.uuid4().hex[:8]}"
    
    update_task_status(task_id, "queued", "Embeddings task queued for processing", 0)
    
    background_tasks.add_task(run_embeddings_async, client_id, task_id)
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="Embeddings task has been queued. Check status using task_id."
    )

@app.get("/client/me/task-status/{task_id}")
async def get_task_status(task_id: str, client_id: str = Depends(get_client_from_header)):
    """Get status of a background task"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify task belongs to client (basic security)
    if not task_id.startswith(f"crawl_{client_id}") and not task_id.startswith(f"embed_{client_id}") and not task_id.startswith(f"crawl_embed_{client_id}"):
        raise HTTPException(status_code=403, detail="Access denied to this task")
    
    return task_status[task_id]

@app.get("/client/me/tasks")
async def get_client_tasks(client_id: str = Depends(get_client_from_header)):
    """Get all tasks for a client"""
    client_tasks = {
        k: v for k, v in task_status.items() 
        if k.startswith(f"crawl_{client_id}") or 
           k.startswith(f"embed_{client_id}") or 
           k.startswith(f"crawl_embed_{client_id}")
    }
    return {"tasks": client_tasks}

@app.post("/client/upload-qa/me")
async def upload_qa(
    file: UploadFile = File(...), 
    client_id: str = Depends(get_client_from_header)
):
    """Upload Q&A file asynchronously"""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_dir, exist_ok=True)
    file_path = os.path.join(client_dir, "custom_qa.json")
    
    # Use aiofiles for async file operations
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    
    return {"status": "success", "message": f"Uploaded Q&A for {client_id}"}

@app.get("/client/status/me")
async def check_status(client_id: str = Depends(get_client_from_header)):
    """Check client data status"""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    return {
        "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
        "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
        "embedded": True  # You might want to check actual embedding status
    }

# ----------------------------
# CLEANUP AND MONITORING
# ----------------------------

@app.get("/admin/system-status")
async def system_status():
    """Get system status and active tasks"""
    return {
        "active_tasks": len([t for t in task_status.values() if t["status"] == "running"]),
        "total_tasks": len(task_status),
        "io_thread_pool": {
            "max_workers": io_executor._max_workers,
            # Note: _threads is private, in production use a proper monitoring solution
        },
        "process_pool": {
            "max_workers": process_executor._max_workers,
        }
    }

@app.delete("/admin/cleanup-tasks")
async def cleanup_old_tasks():
    """Clean up old completed/failed tasks (older than 1 hour)"""
    cutoff_time = datetime.now() - timedelta(hours=1)
    cleaned_count = 0
    
    tasks_to_remove = []
    for task_id, task_data in task_status.items():
        task_time = datetime.fromisoformat(task_data["updated_at"])
        if task_time < cutoff_time and task_data["status"] in ["completed", "failed"]:
            tasks_to_remove.append(task_id)
    
    for task_id in tasks_to_remove:
        del task_status[task_id]
        cleaned_count += 1
    
    return {"cleaned_tasks": cleaned_count, "remaining_tasks": len(task_status)}

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    io_executor.shutdown(wait=True)
    process_executor.shutdown(wait=True)