"""
Enhanced Interactive RAG Chatbot with Structure-Aware Context Handling
Properly interprets tables, lists, and structured data
"""

import os
import json
import threading
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from backend.config import settings
from groq import Groq
from sentence_transformers import SentenceTransformer
from chromadb import PersistentClient

# Configuration
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "ChromaDatabase", "vector-database", "chroma_db"))
CLIENT_DATA_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "client_data"))

EMBEDDING_MODEL = "multi-qa-mpnet-base-dot-v1"
GROQ_MODEL = settings.GROQ_MODEL
GROQ_API_KEY = settings.GROQ_API_KEY

# Global singletons
_embedder_lock = threading.Lock()
_groq_lock = threading.Lock()
_sentence_model: Optional[SentenceTransformer] = None
_groq_client: Optional[Groq] = None
_chroma_client: Optional[PersistentClient] = None
_chatbot_sessions: Dict[str, 'InteractiveRAGChatbot'] = {}
_session_lock = threading.Lock()


def _get_sentence_model() -> SentenceTransformer:
    global _sentence_model
    if _sentence_model is None:
        with _embedder_lock:
            if _sentence_model is None:
                _sentence_model = SentenceTransformer(EMBEDDING_MODEL)
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
        os.makedirs(CHROMA_DB_DIR, exist_ok=True)
        _chroma_client = PersistentClient(path=CHROMA_DB_DIR)
    return _chroma_client


# ──────────────────────────────────────────────────────────────────────────────
# Query Processing
# ──────────────────────────────────────────────────────────────────────────────

class QueryProcessor:
    """Advanced query processing with intent detection."""

    INTENT_PATTERNS = {
        'contact': ['contact', 'phone', 'email', 'reach', 'call', 'address', 'location'],
        'pricing': ['price', 'cost', 'fee', 'charge', 'expensive', 'cheap', 'rate', 'scholarship', 'tuition'],
        'timing': ['hour', 'time', 'schedule', 'when', 'open', 'close', 'timing'],
        'process': ['how', 'apply', 'register', 'enroll', 'signup', 'process', 'step'],
        'information': ['what', 'about', 'tell', 'describe', 'explain', 'information'],
        'comparison': ['vs', 'versus', 'compare', 'difference', 'better', 'which'],
        'availability': ['available', 'offer', 'provide', 'have', 'get'],
    }

    @staticmethod
    def detect_intent(query: str) -> str:
        query_lower = query.lower()
        intent_scores = {}
        for intent, keywords in QueryProcessor.INTENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                intent_scores[intent] = score
        return max(intent_scores, key=intent_scores.get) if intent_scores else 'general'

    @staticmethod
    def preprocess(query: str) -> str:
        import re
        query = re.sub(r'[^\w\s?!.,\-\'"]', '', query)
        return ' '.join(query.split()).strip()


# ──────────────────────────────────────────────────────────────────────────────
# Hybrid Retrieval System
# ──────────────────────────────────────────────────────────────────────────────

class HybridRetriever:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.embedder = _get_sentence_model()
        self.collection = self._get_collection()
        self.custom_qa = self._load_custom_qa()
        self.query_processor = QueryProcessor()

    def _get_collection(self):
        try:
            chroma = _get_chroma()
            return chroma.get_collection(self.client_id.lower())
        except Exception as e:
            print(f"⚠️ Collection not found for {self.client_id}: {e}")
            return None

    def _load_custom_qa(self) -> List[Dict[str, Any]]:
        qa_path = os.path.join(CLIENT_DATA_DIR, self.client_id, "custom_qa.json")
        if not os.path.exists(qa_path):
            return []
        try:
            with open(qa_path, 'r', encoding='utf-8') as f:
                qa_data = json.load(f)
            processed_qa = []
            for item in qa_data:
                questions = item.get("questions", [])
                if not questions and "question" in item:
                    questions = [item["question"]]
                if questions and item.get("answer"):
                    embeddings = [self.embedder.encode(q) for q in questions]
                    processed_qa.append({
                        "questions": questions,
                        "answer": item["answer"],
                        "embeddings": embeddings,
                        "metadata": item.get("metadata", {})
                    })
            return processed_qa
        except Exception as e:
            print(f"⚠️ Error loading custom Q&A: {e}")
            return []

    def match_custom_qa(self, query: str, threshold: float = 0.75) -> Optional[Dict[str, Any]]:
        if not self.custom_qa:
            return None
        query_emb = self.embedder.encode(query)
        best_match = {'score': -1.0, 'answer': None, 'question': None, 'metadata': {}}
        for qa in self.custom_qa:
            for q_text, emb in zip(qa["questions"], qa["embeddings"]):
                from sentence_transformers import util
                similarity = util.cos_sim(query_emb, emb).item()
                query_words = set(query.lower().split())
                qa_words = set(q_text.lower().split())
                overlap = len(query_words & qa_words) / max(len(query_words), len(qa_words))
                combined_score = 0.85 * similarity + 0.15 * overlap
                if combined_score > best_match['score']:
                    best_match = {'score': combined_score, 'answer': qa["answer"], 'question': q_text, 'metadata': qa.get("metadata", {})}
        adjusted_threshold = threshold + (0.05 if len(query.split()) < 5 else 0)
        if best_match['score'] >= adjusted_threshold:
            return {
                'answer': best_match['answer'],
                'confidence': 'high' if best_match['score'] >= 0.88 else 'medium',
                'matched_question': best_match['question'],
                'score': best_match['score'],
                'source': 'custom_qa',
                'metadata': best_match['metadata']
            }
        return None

    def retrieve_documents(self, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        if not self.collection:
            return []
        clean_query = self.query_processor.preprocess(query)
        try:
            q_emb = self.embedder.encode(clean_query)
            results = self.collection.query(query_embeddings=[q_emb.tolist()], n_results=top_k)
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]
            all_results = []
            for doc, meta, dist, doc_id in zip(docs, metas, distances, ids):
                similarity = 1 / (1 + dist)
                all_results.append({'content': doc, 'metadata': meta, 'score': similarity, 'id': doc_id})
            return all_results
        except Exception as e:
            print(f"⚠️ Retrieval error: {e}")
            return []


# ──────────────────────────────────────────────────────────────────────────────
# Interactive RAG Chatbot
# ──────────────────────────────────────────────────────────────────────────────

class InteractiveRAGChatbot:
    """Interactive RAG chatbot with structure-aware prompts."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.retriever = HybridRetriever(client_id)
        self.groq_client = _get_groq_client()
        self.conversation_history = []
        self.client_metadata = self._load_client_metadata()

    def _load_client_metadata(self) -> Dict[str, Any]:
        metadata_path = os.path.join(CLIENT_DATA_DIR, self.client_id, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"domain": "general", "business_type": "organization", "tone": "professional and helpful"}

    def _build_context_string(self, documents: List[Dict[str, Any]], max_tokens: int = 3500) -> str:
        """Build context string with structure awareness."""
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4

        # Prioritize table content for financial queries
        has_tables = any(doc['metadata'].get('contains_table', False) for doc in documents)

        for doc in documents:
            content = doc['content'].strip()
            meta = doc['metadata']

            # Build source info
            source_info = ""
            if meta.get('source') == 'crawl':
                source_info = f"[Source: {meta.get('title', 'Web Page')}]"
                if meta.get('content_type') == 'table':
                    source_info += " [STRUCTURED TABLE DATA]"
            elif meta.get('source') == 'pdf':
                source_info = f"[Source: {meta.get('filename', 'PDF')}]"
            elif meta.get('source') == 'qa':
                source_info = "[Source: Official Q&A]"

            doc_text = f"{source_info}\n{content}\n"

            if total_chars + len(doc_text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 200:
                    context_parts.append(doc_text[:remaining] + "...")
                break

            context_parts.append(doc_text)
            total_chars += len(doc_text)

        return "\n---\n".join(context_parts)

    def _create_structure_aware_prompt(self, query: str, context: str, intent: str) -> str:
        """Create prompt with special instructions for structured data."""
        tone = self.client_metadata.get("tone", "professional and helpful")
        business_type = self.client_metadata.get("business_type", "organization")

        # Detect if context contains tables
        has_tables = '|' in context and context.count('|') > 5
        has_pricing = any(word in context.lower() for word in ['scholarship', 'fee', 'tuition', 'price', 'cost'])

        table_instructions = ""
        if has_tables:
            table_instructions = """

CRITICAL INSTRUCTIONS FOR TABLE DATA:
- The context contains MARKDOWN TABLES with columns separated by |
- Each column has a specific meaning - pay attention to column headers
- When you see numbers in different columns, they represent DIFFERENT values
- For pricing/financial tables:
  * "Scholarship Amount" or similar columns show DISCOUNTS (amount deducted)
  * "Fee After Scholarship" or similar columns show ACTUAL AMOUNT TO PAY
  * Always clarify which number represents what
- Read the "Table Context" and "Important Note" sections carefully
- If a table has explanatory notes, include that information in your answer"""

        if has_pricing and has_tables:
            table_instructions += """
- **IMPORTANT**: When discussing scholarships/fees, always explain:
  1. What is the scholarship/discount amount
  2. What is the final amount the person pays
  3. The relationship between these numbers"""

        return f"""You are an intelligent assistant for a {business_type}. You excel at understanding structured data like tables and lists.

CONTEXT:
{context}
{table_instructions}

GUIDELINES:
1. Answer using the context above
2. When the context contains tables, carefully read column headers to understand what each value represents
3. Be specific with details (numbers, dates, names) and always clarify what each number means
4. Use a {tone} tone
5. Keep answers concise (2-4 sentences) unless detail is needed
6. If you see related columns in a table, explain the relationship between values
7. Always use the most recent and specific information from the context

USER QUESTION: {query}

ANSWER:"""

    def chat(self, query: str, include_history: bool = True, max_history: int = 3) -> Dict[str, Any]:
        """Main chat method with structure-aware processing."""
        if not query or not query.strip():
            return {
                "answer": "I'm here to help! What would you like to know?",
                "confidence": "none",
                "sources": [],
                "type": "prompt"
            }

        start_time = datetime.now()

        # Check custom Q&A first
        custom_match = self.retriever.match_custom_qa(query)
        if custom_match and custom_match['confidence'] == 'high':
            response = {
                "answer": custom_match['answer'],
                "confidence": custom_match['confidence'],
                "sources": [{"type": "custom_qa", "title": "Official Q&A"}],
                "type": "custom_qa",
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
            self._update_history(query, response['answer'])
            return response

        # Retrieve documents
        intent = self.retriever.query_processor.detect_intent(query)

        # Increase top_k for pricing/table queries
        top_k = 15 if intent == 'pricing' else 12
        documents = self.retriever.retrieve_documents(query, top_k=top_k)

        if not documents:
            return {
                "answer": "I couldn't find specific information about that. Could you rephrase or provide more details?",
                "confidence": "none",
                "sources": [],
                "type": "no_results",
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

        # Build context
        context = self._build_context_string(documents)

        if include_history and self.conversation_history:
            history_context = self._format_history(max_history)
            context = f"{history_context}\n\n---\n\nCURRENT CONTEXT:\n{context}"

        # Generate response with structure-aware prompt
        prompt = self._create_structure_aware_prompt(query, context, intent)

        try:
            completion = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Lower temperature for more precise answers
                top_p=0.9,
                max_tokens=600,
                stream=False
            )
            answer = completion.choices[0].message.content.strip()
        except Exception as e:
            return {
                "answer": "I encountered an error. Could you try rephrasing?",
                "confidence": "error",
                "sources": [],
                "type": "llm_error",
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

        confidence = self._estimate_confidence(documents, answer)

        # Build sources
        sources = []
        for doc in documents[:5]:
            meta = doc['metadata']
            source_info = {"score": doc['score']}
            if meta.get('source') == 'crawl':
                source_info.update({
                    "type": "webpage",
                    "title": meta.get('title', 'Web Page'),
                    "url": meta.get('url', ''),
                    "is_structured": meta.get('is_structured', False)
                })
            elif meta.get('source') == 'pdf':
                source_info.update({"type": "document", "title": meta.get('filename', 'PDF')})
            elif meta.get('source') == 'qa':
                source_info.update({"type": "qa", "title": "Custom Q&A"})
            sources.append(source_info)

        response = {
            "answer": answer,
            "confidence": confidence,
            "sources": sources,
            "type": "rag",
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "metadata": {
                "intent": intent,
                "num_documents": len(documents),
                "has_structured_data": any(s.get('is_structured') for s in sources)
            }
        }

        self._update_history(query, answer)
        return response

    def _estimate_confidence(self, documents: List[Dict[str, Any]], answer: str) -> str:
        """Estimate response confidence."""
        if not documents:
            return "none"

        avg_score = sum(d['score'] for d in documents[:5]) / min(len(documents), 5)

        uncertainty_phrases = ["don't have", "not sure", "unclear", "may vary", "recommend contacting"]
        has_uncertainty = any(phrase in answer.lower() for phrase in uncertainty_phrases)

        # Higher confidence for structured data answers
        has_structured = any(d['metadata'].get('is_structured', False) for d in documents[:3])

        if has_uncertainty:
            return "low"
        elif avg_score >= 0.75 and len(documents) >= 3:
            return "high" if has_structured else "medium"
        elif avg_score >= 0.60:
            return "medium"

        return "low"

    def _update_history(self, query: str, answer: str, max_history: int = 10):
        """Update conversation history."""
        self.conversation_history.append({
            "query": query,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]

    def _format_history(self, max_turns: int = 3) -> str:
        """Format recent conversation history."""
        if not self.conversation_history:
            return ""
        recent = self.conversation_history[-max_turns:]
        history_lines = ["RECENT CONVERSATION:"]
        for turn in recent:
            history_lines.append(f"User: {turn['query']}")
            history_lines.append(f"Assistant: {turn['answer']}\n")
        return "\n".join(history_lines)

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary."""
        if not self.conversation_history:
            return {"total_turns": 0, "topics_discussed": [], "last_interaction": None}

        all_queries = " ".join([turn['query'] for turn in self.conversation_history])
        intent_counts = {}
        for intent, keywords in QueryProcessor.INTENT_PATTERNS.items():
            count = sum(1 for kw in keywords if kw in all_queries.lower())
            if count > 0:
                intent_counts[intent] = count

        return {
            "total_turns": len(self.conversation_history),
            "topics_discussed": list(intent_counts.keys()),
            "last_interaction": self.conversation_history[-1]['timestamp']
        }


# ──────────────────────────────────────────────────────────────────────────────
# Public API & Session Management
# ──────────────────────────────────────────────────────────────────────────────

def _get_or_create_session(client_id: str, session_id: Optional[str] = None) -> Tuple[InteractiveRAGChatbot, str]:
    """Get or create chat session."""
    global _chatbot_sessions
    if session_id is None:
        session_id = f"{client_id}_{datetime.now().timestamp()}"
    session_key = f"{client_id}:{session_id}"
    with _session_lock:
        if session_key not in _chatbot_sessions:
            _chatbot_sessions[session_key] = InteractiveRAGChatbot(client_id)
        return _chatbot_sessions[session_key], session_id



def chat_with_model(
    client_id: str,
    query: str,
    session_id: Optional[str] = None,
    include_history: bool = True,
    enable_clarifications: bool = True  # Kept for backward compatibility
) -> Dict[str, Any]:
    """Main chat interface."""
    chatbot, session_id = _get_or_create_session(client_id, session_id)
    response = chatbot.chat(query, include_history=include_history)
    response['session_id'] = session_id
    return response



def get_conversation_state(client_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Get conversation state."""
    if session_id:
        chatbot, _ = _get_or_create_session(client_id, session_id)
        return chatbot.get_conversation_summary()
    return {"total_turns": 0, "topics_discussed": [], "last_interaction": None, "message": "No active session"}


def reset_conversation(client_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Reset conversation history."""
    global _chatbot_sessions
    if session_id:
        session_key = f"{client_id}:{session_id}"
        with _session_lock:
            if session_key in _chatbot_sessions:
                _chatbot_sessions[session_key].clear_history()
                return {"status": "success", "message": f"History cleared for {session_id}"}
    return {"status": "success", "message": "No active session"}


def clear_session(client_id: str, session_id: str) -> Dict[str, Any]:
    """Clear a specific session."""
    global _chatbot_sessions
    session_key = f"{client_id}:{session_id}"
    with _session_lock:
        if session_key in _chatbot_sessions:
            del _chatbot_sessions[session_key]
            return {"status": "success", "message": f"Session {session_id} removed"}
    return {"status": "not_found", "message": "Session not found"}


def cleanup_old_sessions(max_age_hours: int = 24) -> Dict[str, Any]:
    """Clean up old inactive sessions."""
    global _chatbot_sessions
    current_time = datetime.now()
    removed_count = 0

    with _session_lock:
        sessions_to_remove = []
        for session_key, chatbot in _chatbot_sessions.items():
            if chatbot.conversation_history:
                last_interaction = datetime.fromisoformat(
                    chatbot.conversation_history[-1]['timestamp']
                )
                age_hours = (current_time - last_interaction).total_seconds() / 3600

                if age_hours > max_age_hours:
                    sessions_to_remove.append(session_key)

        for session_key in sessions_to_remove:
            del _chatbot_sessions[session_key]
            removed_count += 1

    return {
        "status": "success",
        "removed_sessions": removed_count,
        "active_sessions": len(_chatbot_sessions),
        "message": f"Cleaned up {removed_count} old sessions"
    }


def explain_context(client_id: str, query: str) -> Dict[str, Any]:
    """
    Debug function to see retrieved context and document analysis.
    Useful for understanding what the RAG system is finding.

    Args:
        client_id: Client identifier
        query: User query to analyze

    Returns:
        Retrieved documents with scores, metadata, and analysis
    """
    retriever = HybridRetriever(client_id)
    documents = retriever.retrieve_documents(query, top_k=15)
    intent = retriever.query_processor.detect_intent(query)

    # Analyze retrieved documents
    has_tables = any(doc['metadata'].get('contains_table', False) for doc in documents)
    has_structured = any(doc['metadata'].get('is_structured', False) for doc in documents)

    return {
        "query": query,
        "intent": intent,
        "num_documents": len(documents),
        "has_tables": has_tables,
        "has_structured_data": has_structured,
        "documents": [
            {
                "content": doc['content'][:300] + "..." if len(doc['content']) > 300 else doc['content'],
                "score": doc['score'],
                "metadata": doc['metadata']
            }
            for doc in documents[:10]
        ]
    }


# Backward compatibility
UniversalRAGChatbot = InteractiveRAGChatbot
