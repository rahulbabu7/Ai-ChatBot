import os
import json
import threading
import re
from functools import lru_cache
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer, CrossEncoder, util
from chromadb import PersistentClient

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Config
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Chroma DB lives inside Chatbot repo
CHROMA_DB_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..","..","chatbot", "vector-database", "chroma_db"))

# Client data lives in backend/client_data/<client_id>/
BACKEND_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "backend"))
CLIENT_DATA_DIR = os.path.join(BACKEND_ROOT, "client_data")

# Groq model
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ──────────────────────────────────────────────────────────────────────────────
# Global singletons with lazy init
# ──────────────────────────────────────────────────────────────────────────────
_embedder_lock = threading.Lock()
_reranker_lock = threading.Lock()
_groq_lock = threading.Lock()
_sentence_model: Optional[SentenceTransformer] = None
_reranker_model: Optional[CrossEncoder] = None
_groq_client: Optional[Groq] = None
_chroma_client: Optional[PersistentClient] = None


def _get_sentence_model() -> SentenceTransformer:
    global _sentence_model
    if _sentence_model is None:
        with _embedder_lock:
            if _sentence_model is None:
                _sentence_model = SentenceTransformer("multi-qa-mpnet-base-dot-v1")
    return _sentence_model


def _get_reranker() -> CrossEncoder:
    """Initialize cross-encoder for reranking retrieved documents."""
    global _reranker_model
    if _reranker_model is None:
        with _reranker_lock:
            if _reranker_model is None:
                print("🔄 Loading reranker model...")
                _reranker_model = CrossEncoder('cross-encoder/ms-marco-electra-base')
    return _reranker_model


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
# Query Processing
# ──────────────────────────────────────────────────────────────────────────────
def preprocess_query(query: str) -> str:
    """Clean and normalize query."""
    # Remove excessive special characters but keep important punctuation
    query = re.sub(r'[^\w\s?!.,\-]', '', query)
    # Normalize whitespace
    query = ' '.join(query.split())
    return query.strip()


def expand_query(query: str) -> str:
    """Add synonyms and related terms to improve retrieval."""
    expansions = {
        'admission': 'admission enrollment application apply',
        'admissions': 'admission enrollment application apply',
        'fees': 'fees cost tuition charges payment price',
        'fee': 'fees cost tuition charges payment price',
        'courses': 'courses programs degrees majors curriculum',
        'course': 'courses programs degrees majors curriculum',
        'faculty': 'faculty professors teachers staff instructor',
        'contact': 'contact phone email address location reach',
        'facilities': 'facilities infrastructure amenities resources',
        'placement': 'placement job career recruitment companies',
        'hostel': 'hostel accommodation residence housing',
        'library': 'library books resources study',
        'scholarship': 'scholarship financial aid assistance',
    }

    query_lower = query.lower()
    expanded_terms = set()

    for key, expansion in expansions.items():
        if key in query_lower:
            expanded_terms.update(expansion.split())

    # Remove terms already in query
    query_words = set(query.lower().split())
    new_terms = expanded_terms - query_words

    if new_terms:
        return f"{query} {' '.join(new_terms)}"
    return query


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
    """
    path = _custom_qa_path(client_id)

    if not os.path.exists(path):
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
        _load_custom_qa_cached.cache_clear()
    except Exception:
        pass
    _ = _load_custom_qa_cached(client_id)


def find_custom_answer(client_id: str, query: str, threshold: float = 0.72) -> Optional[Dict[str, Any]]:
    """
    Enhanced custom Q&A matching with multiple strategies.
    Returns dict with answer and confidence if found, else None.
    """
    qa_entries = _load_custom_qa_cached(client_id)

    if not qa_entries:
        return None

    model = _get_sentence_model()
    q_emb = model.encode(query)

    best_match = {'score': -1.0, 'answer': None, 'question': None}

    for qa in qa_entries:
        for q_text, emb in zip(qa["questions"], qa["embeddings"]):
            # Semantic similarity
            semantic_score = util.cos_sim(q_emb, emb).item()

            # Keyword overlap boost
            query_words = set(query.lower().split())
            qa_words = set(q_text.lower().split())
            overlap = len(query_words & qa_words) / len(query_words | qa_words) if (query_words | qa_words) else 0

            # Combined score (80% semantic, 20% keyword)
            combined_score = 0.8 * semantic_score + 0.2 * overlap

            if combined_score > best_match['score']:
                best_match = {
                    'score': combined_score,
                    'answer': qa["answer"],
                    'question': q_text
                }

    # Dynamic threshold based on query length (shorter queries need higher confidence)
    dynamic_threshold = threshold if len(query.split()) > 4 else threshold + 0.05

    if best_match['score'] >= dynamic_threshold:
        confidence = "high" if best_match['score'] >= 0.85 else "medium"
        return {
            'answer': best_match['answer'],
            'confidence': confidence,
            'matched_question': best_match['question'],
            'score': best_match['score']
        }
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Retrieval from Chroma with Reranking
# ──────────────────────────────────────────────────────────────────────────────
def _get_collection(client_id: str):
    chroma = _get_chroma()
    try:
        return chroma.get_collection(client_id)
    except Exception:
        return None


def retrieve_context(client_id: str, query: str, top_k: int = 12, max_chars: int = 2000) -> Dict[str, Any]:
    """
    Enhanced retrieval with reranking and query expansion.
    Returns:
      {
        "text": "<concatenated context>",
        "sources": [...],
        "confidence": "high|medium|low"
      }
    """
    # Preprocess and expand query
    processed_query = preprocess_query(query)
    expanded_query = expand_query(processed_query)

    coll = _get_collection(client_id)
    if coll is None:
        return {"text": "", "sources": [], "confidence": "none"}

    try:
        # Retrieve more candidates for reranking
        model = _get_sentence_model()
        query_embedding = model.encode(expanded_query)
        res = coll.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        docs = res.get("documents", [[]])[0] if res.get("documents") else []
        metas = res.get("metadatas", [[]])[0] if res.get("metadatas") else []
    except Exception as e:
        print(f"⚠️ Retrieval error: {e}")
        return {"text": "", "sources": [], "confidence": "none"}

    if not docs:
        return {"text": "", "sources": [], "confidence": "none"}

    # Rerank using cross-encoder (use original query for relevance)
    reranker = _get_reranker()
    pairs = [[processed_query, doc] for doc in docs]
    scores = reranker.predict(pairs)

    # Sort by reranking scores
    ranked = sorted(zip(docs, metas, scores), key=lambda x: x[2], reverse=True)

    # Build context from top reranked results
    buf = []
    total = 0
    used_metas = []
    relevance_scores = []

    # Use top 6 after reranking
    for doc, meta, score in ranked[:6]:
        if not doc or not doc.strip():
            continue
        if total + len(doc) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                buf.append(doc[:remaining] + "...")
                used_metas.append(meta)
                relevance_scores.append(score)
                total += remaining
            break
        buf.append(doc)
        used_metas.append(meta)
        relevance_scores.append(score)
        total += len(doc)

    if not buf:
        return {"text": "", "sources": [], "confidence": "none"}

    text = "\n\n---\n\n".join(buf)
    sources = []

    for m in used_metas:
        source_info = {"source": m.get("source", "unknown")}

        if m.get("source") == "crawl":
            source_info.update({
                "url": m.get("url", ""),
                "title": m.get("title", "")
            })
        elif m.get("source") == "pdf":
            source_info.update({
                "filename": m.get("filename", ""),
                "title": m.get("title", "PDF Document")
            })
        elif m.get("source") == "qa":
            source_info.update({
                "title": "Custom Q&A",
                "type": "qa"
            })

        sources.append(source_info)

    # Estimate confidence based on relevance scores and context length
    avg_score = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
    confidence = "low"
    if avg_score > 5.0 and len(sources) >= 3:
        confidence = "high"
    elif avg_score > 2.0 or len(sources) >= 2:
        confidence = "medium"

    return {
        "text": text.strip(),
        "sources": sources,
        "confidence": confidence
    }


# ──────────────────────────────────────────────────────────────────────────────
# Prompting & Generation (Groq)
# ──────────────────────────────────────────────────────────────────────────────
def _build_prompt(client_id: str, context_text: str, user_input: str) -> str:
    """Enhanced prompt template with better instructions."""
    system_prompt = """You are a helpful and knowledgeable college information assistant. Follow these rules:

1. ONLY use information from the CONTEXT below to answer questions
2. If the answer isn't in the context, say "I don't have that specific information in my knowledge base"
3. Be specific and include relevant details (numbers, dates, requirements, etc.)
4. Keep answers concise but complete (2-4 sentences typically)
5. If the context has partial information, provide what you can and note what's missing
6. For contact/admission questions, include specific details like phone numbers, emails, dates if available
7. Use a friendly, professional tone appropriate for students and parents
8. Do not make up or assume information not in the context

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    return system_prompt.format(
        context=context_text or "[No relevant information found in the knowledge base]",
        question=user_input
    )


def _generate_llm_response(prompt: str) -> str:
    client = _get_groq_client()
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for more focused responses
            top_p=0.9,
            max_tokens=400,
            stream=False,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as e:
        return f"⚠️ Error generating response: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# Public API (call from FastAPI)
# ──────────────────────────────────────────────────────────────────────────────
def chat_with_model(client_id: str, query: str) -> Dict[str, Any]:
    """
    Enhanced chat entry point with confidence scoring.
    Returns:
      {
        "answer": str,
        "confidence": "high|medium|low|none",
        "sources": [...],
        "type": "custom_qa|rag|fallback"
      }
    """
    q = (query or "").strip()
    if not q:
        return {
            "answer": "Please enter a question.",
            "confidence": "none",
            "sources": [],
            "type": "error"
        }

    # 1) Custom QA - Direct answers with semantic matching (PRIORITY)
    custom_result = find_custom_answer(client_id, q)
    if custom_result:
        return {
            "answer": custom_result['answer'],
            "confidence": custom_result['confidence'],
            "sources": [{"type": "custom_qa", "title": "Pre-configured Answer"}],
            "type": "custom_qa",
            "debug_score": custom_result.get('score', 0)
        }

    # 2) Retrieval Augmented Generation - Vector database search
    ctx = retrieve_context(client_id, q, top_k=12, max_chars=2000)
    if ctx["text"]:
        prompt = _build_prompt(client_id, ctx["text"], q)
        answer = _generate_llm_response(prompt)

        return {
            "answer": answer,
            "confidence": ctx["confidence"],
            "sources": ctx["sources"],
            "type": "rag"
        }

    # 3) Fallback
    return {
        "answer": "I couldn't find that information in this client's knowledge base. Please try rephrasing your question or contact the college directly for more details.",
        "confidence": "none",
        "sources": [],
        "type": "fallback"
    }


def explain_context(client_id: str, query: str) -> Dict[str, Any]:
    """
    For debugging: returns the retrieved text+sources+confidence.
    """
    return retrieve_context(client_id, query)
