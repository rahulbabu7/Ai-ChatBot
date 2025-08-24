# import sys
# import os
# from fastapi import FastAPI
# from pydantic import BaseModel
# from fastapi.middleware.cors import CORSMiddleware

# # Ensure parent directory is in Python path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from Chatbot.llm.llm import chat_with_model, retrieve_context

# app = FastAPI()

# # Allow frontend (React) to call API
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],  
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# class ChatRequest(BaseModel):
#     message: str

# @app.post("/chat")
# def chat_endpoint(req: ChatRequest):
#     answer = chat_with_model(req.message)
#     return {"reply": answer}

# @app.post("/context")
# def context_endpoint(req: ChatRequest):
#     context = retrieve_context(req.message)
#     return {"context": context or "No relevant context found."}


# import os
# import sys
# import shutil
# import subprocess
# from fastapi import FastAPI, UploadFile, File
# from pydantic import BaseModel
# from fastapi.middleware.cors import CORSMiddleware

# # Add parent dir to path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from Chatbot.llm.llm import chat_with_model, retrieve_context

# # === FastAPI App ===
# app = FastAPI()

# # Allow frontend (React) to call API
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],  
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # === Paths ===
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# CLIENTS_DIR = os.path.join(BASE_DIR, "client_data")
# CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))

# os.makedirs(CLIENTS_DIR, exist_ok=True)

# # ----------------------------
# # 🔹 Models
# # ----------------------------
# class ChatRequest(BaseModel):
#     message: str
#     client_id: str

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
#     answer = chat_with_model(req.message, req.client_id)
#     return {"reply": answer}

# @app.post("/context")
# def context_endpoint(req: ChatRequest):
#     context = retrieve_context(req.message, req.client_id)
#     return {"context": context or "No relevant context found."}

# # ----------------------------
# # 🔹 ADMIN ENDPOINTS
# # ----------------------------
# @app.post("/admin/crawl")
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

# @app.post("/admin/upload-qa/{client_id}")
# async def upload_qa(client_id: str, file: UploadFile = File(...)):
#     """Upload custom Q&A JSON for a client."""
#     client_dir = os.path.join(CLIENTS_DIR, client_id)
#     os.makedirs(client_dir, exist_ok=True)

#     file_path = os.path.join(client_dir, "custom_qa.json")
#     with open(file_path, "wb") as f:
#         shutil.copyfileobj(file.file, f)

#     return {"status": "success", "message": f"Uploaded Q&A for {client_id}"}

# @app.post("/admin/embed/{client_id}")
# def run_embeddings(client_id: str):
#     """Run chunking + embeddings + ingest into Chroma."""
#     try:
        
#         script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
#         print(script_path)
#         subprocess.run([sys.executable, script_path, client_id], check=True)
#         return {"status": "success", "message": f"Embeddings + ingestion done for {client_id}"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

# @app.get("/admin/status/{client_id}")
# def check_status(client_id: str):
#     """Check if crawl, Q&A, and embeddings exist."""
#     client_dir = os.path.join(CLIENTS_DIR, client_id)
#     if not os.path.exists(client_dir):
#         return {"status": "not_found"}

#     return {
#         "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
#         "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
#         "embedded": os.path.exists(os.path.join(client_dir, "chroma_db")),
#     }

# # ----------------------------
# # 🔹 CLIENT MANAGEMENT
# # ----------------------------
# # Temporary in-memory client storage
# CLIENTS = []

# @app.get("/admin/clients")
# def list_clients():
#     return {"clients": CLIENTS}

# @app.post("/admin/add-client")
# def add_client(req: ClientRequest):
#     if req.client_id not in CLIENTS:
#         CLIENTS.append(req.client_id)
#     return {"message": f"Client '{req.client_id}' added.", "clients": CLIENTS}




import os
import sys
import shutil
import subprocess
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Add Chatbot/llm to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/llm"))
sys.path.append(CHATBOT_LLM_DIR)

from llm_service import chat_with_model, explain_context  # ✅ updated import

# === FastAPI App ===
app = FastAPI()

# Allow frontend (React) to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:5174"],
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
    client_id: str
    message: str

class CrawlRequest(BaseModel):
    client_id: str
    allowed_domain: str
    start_url: str

class ClientRequest(BaseModel):
    client_id: str

# ----------------------------
# 🔹 CHAT ENDPOINTS
# ----------------------------
@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    answer = chat_with_model(req.client_id, req.message)  # ✅ fixed order
    return {"reply": answer}

@app.post("/context")
def context_endpoint(req: ChatRequest):
    ctx = explain_context(req.client_id, req.message)  # ✅ use explain_context
    return {"context": ctx or "No relevant context found."}

# ----------------------------
# 🔹 ADMIN ENDPOINTS
# ----------------------------
@app.post("/admin/crawl")
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

@app.post("/admin/upload-qa/{client_id}")
async def upload_qa(client_id: str, file: UploadFile = File(...)):
    """Upload custom Q&A JSON for a client."""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_dir, exist_ok=True)

    file_path = os.path.join(client_dir, "custom_qa.json")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"status": "success", "message": f"Uploaded Q&A for {client_id}"}

@app.post("/admin/embed/{client_id}")
def run_embeddings(client_id: str):
    """Run chunking + embeddings + ingest into Chroma."""
    try:
        script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
        subprocess.run([sys.executable, script_path, client_id], check=True)
        return {"status": "success", "message": f"Embeddings + ingestion done for {client_id}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/admin/status/{client_id}")
def check_status(client_id: str):
    """Check if crawl, Q&A, and embeddings exist for a client."""
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    if not os.path.exists(client_dir):
        return {"status": "not_found"}

    return {
        "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
        "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
        # embeddings are stored in global Chroma DB, not per client folder
        "embedded": True  # TODO: optionally check Chroma for collection existence
    }

# ----------------------------
# 🔹 CLIENT MANAGEMENT
# ----------------------------
CLIENTS = []

@app.get("/admin/clients")
def list_clients():
    return {"clients": CLIENTS}

@app.post("/admin/add-client")
def add_client(req: ClientRequest):
    if req.client_id not in CLIENTS:
        CLIENTS.append(req.client_id)
    return {"message": f"Client '{req.client_id}' added.", "clients": CLIENTS}
