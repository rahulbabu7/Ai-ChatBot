import sys
import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Ensure parent directory is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Chatbot.llm.llm import chat_with_model, retrieve_context

app = FastAPI()

# Allow frontend (React) to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    answer = chat_with_model(req.message)
    return {"reply": answer}

@app.post("/context")
def context_endpoint(req: ChatRequest):
    context = retrieve_context(req.message)
    return {"context": context or "No relevant context found."}
