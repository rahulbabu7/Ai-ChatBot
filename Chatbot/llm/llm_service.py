import os
import json
import threading
from functools import lru_cache
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer, util
from chromadb import PersistentClient

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Config
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Chroma DB lives inside Chatbot repo
CHROMA_DB_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..","..","chatbot", "vector-database", "chroma_db"))

# Client data lives in backend/client_data/<client_id>/
# (We resolve relative to backend/main app that imports this file.)
# If your backend runs from backend/, this will resolve to that same backend folder.
BACKEND_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "backend"))
CLIENT_DATA_DIR = os.path.join(BACKEND_ROOT, "client_data")

# Groq model
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ──────────────────────────────────────────────────────────────────────────────
# Global singletons with lazy init
# ──────────────────────────────────────────────────────────────────────────────
_embedder_lock = threading.Lock()
_groq_lock = threading.Lock()
_sentence_model: Optional[SentenceTransformer] = None
_groq_client: Optional[Groq] = None
_chroma_client: Optional[PersistentClient] = None


def _get_sentence_model() -> SentenceTransformer:
    global _sentence_model
    if _sentence_model is None:
        with _embedder_lock:
            if _sentence_model is None:
                _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sentence_model


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set in environment.")
        with _groq_lock:
            if _groq_client is None:
                _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _get_chroma() -> PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        if not os.path.exists(CHROMA_DB_DIR):
            os.makedirs(CHROMA_DB_DIR, exist_ok=True)
        _chroma_client = PersistentClient(path=CHROMA_DB_DIR)
    return _chroma_client


# ──────────────────────────────────────────────────────────────────────────────
# Helpers: file paths and loading custom QA per client
# ──────────────────────────────────────────────────────────────────────────────
def _client_dir(client_id: str) -> str:
    return os.path.join(CLIENT_DATA_DIR, client_id)


def _custom_qa_path(client_id: str) -> str:
    return os.path.join(_client_dir(client_id), "custom_qa.json")


@lru_cache(maxsize=128)
def _load_custom_qa_cached(client_id: str) -> List[Dict[str, Any]]:
    """
    Load and embed a client's custom QA once, memoized by client_id.
    JSON format per item:
    {
      "questions": ["q1", "q2", ...],   # OR "question": "single question"
      "answer": "answer text"
    }
    """
    path = _custom_qa_path(client_id)
    if not os.path.exists(path):
        # No custom QA for this client
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return []

    # Normalize to a list of {questions:[], answer:str}
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        if "questions" in item and isinstance(item["questions"], list):
            questions = item["questions"]
        elif "question" in item and isinstance(item["question"], str):
            questions = [item["question"]]
        else:
            # Skip malformed entries
            continue
        normalized.append({"questions": questions, "answer": item.get("answer", "")})

    # Precompute embeddings
    model = _get_sentence_model()
    for qa in normalized:
        qa["embeddings"] = [model.encode(q) for q in qa["questions"]]

    return normalized


def reload_custom_qa_cache(client_id: str) -> None:
    """If you update custom_qa.json, call this to refresh cache."""
    try:
        _load_custom_qa_cached.cache_clear()  # clear all; lightweight enough
    except Exception:
        pass
    # Touch load to repopulate
    _ = _load_custom_qa_cached(client_id)


def find_custom_answer(client_id: str, query: str, threshold: float = 0.8) -> Optional[str]:
    qa_entries = _load_custom_qa_cached(client_id)
    if not qa_entries:
        return None
    model = _get_sentence_model()
    q_emb = model.encode(query)
    best_score = -1.0
    best_answer = None
    for qa in qa_entries:
        for emb in qa["embeddings"]:
            score = util.cos_sim(q_emb, emb).item()
            if score > best_score:
                best_score = score
                best_answer = qa["answer"]
    if best_score >= threshold:
        return best_answer
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Retrieval from Chroma (per-client collection)
# ──────────────────────────────────────────────────────────────────────────────
def _get_collection(client_id: str):
    # We store each client's docs in a collection named exactly the client_id
    chroma = _get_chroma()
    try:
        return chroma.get_collection(client_id)
    except Exception:
        # Collection may not exist yet
        return None


def retrieve_context(client_id: str, query: str, top_k: int = 6, max_chars: int = 1800) -> Dict[str, Any]:
    """
    Returns a dict with:
      {
        "text": "<concatenated context>",
        "sources": [{"url":..., "title":...}, ...]
      }
    If no collection or results, returns {"text": "", "sources": []}.
    """
    coll = _get_collection(client_id)
    if coll is None:
        return {"text": "", "sources": []}

    # Chroma query
    try:
        res = coll.query(query_texts=[query], n_results=top_k)
        docs: List[str] = res.get("documents", [[]])[0] if res.get("documents") else []
        metas: List[Dict[str, Any]] = res.get("metadatas", [[]])[0] if res.get("metadatas") else []
    except Exception:
        return {"text": "", "sources": []}

    if not docs:
        return {"text": "", "sources": []}

    # Concatenate while respecting max_chars
    buf = []
    total = 0
    for d in docs:
        if not d:
            continue
        if total + len(d) > max_chars:
            remaining = max_chars - total
            if remaining > 80:  # only add if meaningful space leftover
                buf.append(d[:remaining])
                total += remaining
            break
        buf.append(d)
        total += len(d)

    text = "\n\n---\n\n".join(buf)
    sources = [{"url": m.get("url", ""), "title": m.get("title", "")} for m in metas[:len(buf)]]
    return {"text": text.strip(), "sources": sources}


# ──────────────────────────────────────────────────────────────────────────────
# Prompting & Generation (Groq)
# ──────────────────────────────────────────────────────────────────────────────
def _build_prompt(client_id: str, context_text: str, user_input: str) -> str:
    system_rules = (
        "You are a helpful assistant for the college website. "
        "Answer only using the provided CONTEXT. "
        "If the answer is not in the context, say you don't have that information."
    )
    header = f"CLIENT: {client_id}\n\nCONTEXT:\n{context_text or '[no context]'}\n\nUSER QUESTION: {user_input}\n\nASSISTANT:"
    return f"{system_rules}\n\n{header}"


def _generate_llm_response(prompt: str) -> str:
    client = _get_groq_client()
    try:
        # Non-streaming for simplicity in the backend function
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            top_p=0.9,
            max_tokens=350,
            stream=False,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as e:
        return f"⚠️ Error generating response: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# Public API (call from FastAPI)
# ──────────────────────────────────────────────────────────────────────────────
def chat_with_model(client_id: str, query: str) -> str:
    """
    Main chat entry point:
      1) Try client-specific custom QA
      2) Else retrieve from client's collection
      3) Else fallback
    """
    q = (query or "").strip()
    if not q:
        return "Please enter a question."

    # 1) Custom QA
    ans = find_custom_answer(client_id, q)
    if ans:
        return ans

    # 2) Retrieval Augmented Generation
    ctx = retrieve_context(client_id, q, top_k=6, max_chars=1800)
    if ctx["text"]:
        prompt = _build_prompt(client_id, ctx["text"], q)
        return _generate_llm_response(prompt)

    # 3) Fallback
    return "I couldn't find that information in this client's knowledge base."


def explain_context(client_id: str, query: str) -> Dict[str, Any]:
    """
    For a `/context` endpoint or debugging in UI: returns the retrieved text+sources.
    """
    return retrieve_context(client_id, query)
