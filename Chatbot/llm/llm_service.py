"""
Enhanced Interactive RAG Chatbot with Automatic Form Collection
- AUTOMATIC form trigger after N messages (NO keywords required)
- Chat continuation with memory
- Structure-aware context handling
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

# Import form collection system
from form_system import FormCollector, FormTemplate, FormStatus

# Configuration
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "ChromaDatabase", "vector-database", "chroma_db"))
CLIENT_DATA_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "client_data"))

EMBEDDING_MODEL = "multi-qa-mpnet-base-dot-v1"
GROQ_MODEL = settings.GROQ_MODEL
GROQ_API_KEY = settings.GROQ_API_KEY

# Form trigger configuration
FORM_TRIGGER_MESSAGE_COUNT = 3  # Trigger form after this many messages

# 🔥 NEW: Trigger modes
FORM_TRIGGER_MODE = "automatic"  # Options: "automatic", "keyword", "both"
# - "automatic": Trigger after N messages (NO keywords needed)
# - "keyword": Trigger only when keywords detected (original behavior)
# - "both": Trigger after N messages AND keywords present

FORM_TRIGGER_KEYWORDS = ['demo', 'schedule', 'book', 'appointment', 'contact', 'meet', 'talk', 'interested']

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
        'action_intent': ['demo', 'schedule', 'book', 'appointment', 'meet', 'talk', 'interested', 'sign up', 'register']
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

    @staticmethod
    def should_trigger_form(query: str, message_count: int, trigger_mode: str) -> bool:
        """
        Determine if form collection should be triggered based on mode.

        Modes:
        - "automatic": Trigger after N messages (default)
        - "keyword": Trigger only with keywords
        - "both": Trigger after N messages AND with keywords
        """
        # Check message count first
        if message_count < FORM_TRIGGER_MESSAGE_COUNT:
            return False

        # Check for action keywords
        query_lower = query.lower()
        has_action_keyword = any(keyword in query_lower for keyword in FORM_TRIGGER_KEYWORDS)

        if trigger_mode == "automatic":
            # 🔥 NEW: Trigger automatically after N messages (NO keywords needed)
            return True
        elif trigger_mode == "keyword":
            # Original behavior: Require keywords
            return has_action_keyword
        elif trigger_mode == "both":
            # Require BOTH message count AND keywords
            return has_action_keyword

        # Default to automatic
        return True


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
# Interactive RAG Chatbot with Form Collection
# ──────────────────────────────────────────────────────────────────────────────

class InteractiveRAGChatbot:
    """Interactive RAG chatbot with automatic form collection and chat continuity."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.retriever = HybridRetriever(client_id)
        self.groq_client = _get_groq_client()
        self.conversation_history = []
        self.client_metadata = self._load_client_metadata()

        # Form collection state
        self.form_collector: Optional[FormCollector] = None
        self.form_triggered = False
        self.user_declined_form = False

        # Message count for form triggering
        self.message_count = 0

    def _load_client_metadata(self) -> Dict[str, Any]:
        metadata_path = os.path.join(CLIENT_DATA_DIR, self.client_id, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "domain": "general",
            "business_type": "organization",
            "tone": "professional and helpful",
            "form_collection": {
                "enabled": True,
                "trigger_after_messages": FORM_TRIGGER_MESSAGE_COUNT,
                "trigger_mode": FORM_TRIGGER_MODE,  # "automatic", "keyword", or "both"
                "form_type": "contact"  # or "demo_booking"
            }
        }

    def _should_trigger_form_collection(self, query: str) -> bool:
        """Check if we should trigger form collection"""
        # Check if form collection is enabled
        if not self.client_metadata.get("form_collection", {}).get("enabled", True):
            return False

        # Don't trigger if already triggered or user declined
        if self.form_triggered or self.user_declined_form:
            return False

        # Get trigger mode from metadata (defaults to "automatic")
        trigger_mode = self.client_metadata.get("form_collection", {}).get("trigger_mode", FORM_TRIGGER_MODE)

        # Check message count and keywords based on mode
        return QueryProcessor.should_trigger_form(query, self.message_count, trigger_mode)

    def _build_context_string(self, documents: List[Dict[str, Any]], max_tokens: int = 3500) -> str:
        """Build context string with structure awareness."""
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4

        has_tables = any(doc['metadata'].get('contains_table', False) for doc in documents)

        for doc in documents:
            content = doc['content'].strip()
            meta = doc['metadata']

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
8. Maintain conversation continuity - reference previous discussion when relevant

USER QUESTION: {query}

ANSWER:"""

    def chat(self, query: str, include_history: bool = True, max_history: int = 5) -> Dict[str, Any]:
        """Main chat method with form collection and conversation continuity."""

        if not query or not query.strip():
            return {
                "answer": "I'm here to help! What would you like to know?",
                "confidence": "none",
                "sources": [],
                "type": "prompt",
                "form_active": False
            }

        start_time = datetime.now()
        self.message_count += 1

        # Handle active form collection
        if self.form_collector and self.form_collector.status == FormStatus.IN_PROGRESS:
            form_result = self.form_collector.process_response(query)

            response = {
                "answer": form_result["message"],
                "confidence": "high",
                "sources": [],
                "type": "form_collection",
                "form_active": not form_result["form_complete"],
                "form_status": form_result["status"],
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

            if form_result["form_complete"]:
                self._update_history(query, form_result["message"])
                response["collected_data"] = form_result.get("collected_data", {})
                response["form_type"] = form_result.get("form_type")

            return response

        # Check if user is declining form
        decline_keywords = ['no thanks', 'not now', 'maybe later', 'no', 'skip']
        if self.form_triggered and any(keyword in query.lower() for keyword in decline_keywords):
            self.user_declined_form = True
            return {
                "answer": "No problem! Feel free to continue asking questions, and let me know if you change your mind.",
                "confidence": "high",
                "sources": [],
                "type": "form_declined",
                "form_active": False,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

        # Check if we should trigger form collection
        if self._should_trigger_form_collection(query):
            self.form_triggered = True
            form_type = self.client_metadata.get("form_collection", {}).get("form_type", "contact")

            if form_type == "demo_booking":
                template = FormTemplate.get_demo_booking_form()
            else:
                template = FormTemplate.get_contact_form()

            self.form_collector = FormCollector(template)
            first_prompt = self.form_collector.start()

            # 🔥 UPDATED: Friendlier intro message for automatic trigger
            intro_message = "Thank you for chatting with us! Before we continue, I'd love to connect with you personally. May I collect a few quick details?\n\n" + first_prompt

            return {
                "answer": intro_message,
                "confidence": "high",
                "sources": [],
                "type": "form_triggered",
                "form_active": True,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

        # Regular RAG processing with conversation continuity
        custom_match = self.retriever.match_custom_qa(query)
        if custom_match and custom_match['confidence'] == 'high':
            response = {
                "answer": custom_match['answer'],
                "confidence": custom_match['confidence'],
                "sources": [{"type": "custom_qa", "title": "Official Q&A"}],
                "type": "custom_qa",
                "form_active": False,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
            self._update_history(query, response['answer'])
            return response

        intent = self.retriever.query_processor.detect_intent(query)
        top_k = 15 if intent == 'pricing' else 12
        documents = self.retriever.retrieve_documents(query, top_k=top_k)

        if not documents:
            return {
                "answer": "I couldn't find specific information about that. Could you rephrase or provide more details?",
                "confidence": "none",
                "sources": [],
                "type": "no_results",
                "form_active": False,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

        context = self._build_context_string(documents)

        # Include conversation history for continuity
        if include_history and self.conversation_history:
            history_context = self._format_history(max_history)
            context = f"{history_context}\n\n---\n\nCURRENT CONTEXT:\n{context}"

        prompt = self._create_structure_aware_prompt(query, context, intent)

        try:
            completion = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
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
                "form_active": False,
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

        confidence = self._estimate_confidence(documents, answer)

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
            "form_active": False,
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "metadata": {
                "intent": intent,
                "num_documents": len(documents),
                "has_structured_data": any(s.get('is_structured') for s in sources),
                "message_count": self.message_count
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
        has_structured = any(d['metadata'].get('is_structured', False) for d in documents[:3])

        if has_uncertainty:
            return "low"
        elif avg_score >= 0.75 and len(documents) >= 3:
            return "high" if has_structured else "medium"
        elif avg_score >= 0.60:
            return "medium"

        return "low"

    def _update_history(self, query: str, answer: str, max_history: int = 10):
        """Update conversation history for continuity."""
        self.conversation_history.append({
            "query": query,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]

    def _format_history(self, max_turns: int = 5) -> str:
        """Format recent conversation history for context."""
        if not self.conversation_history:
            return ""
        recent = self.conversation_history[-max_turns:]
        history_lines = ["RECENT CONVERSATION (for context continuity):"]
        for turn in recent:
            history_lines.append(f"User: {turn['query']}")
            history_lines.append(f"Assistant: {turn['answer']}\n")
        return "\n".join(history_lines)

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.message_count = 0
        self.form_collector = None
        self.form_triggered = False
        self.user_declined_form = False

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary."""
        if not self.conversation_history:
            return {
                "total_turns": 0,
                "topics_discussed": [],
                "last_interaction": None,
                "form_status": "not_triggered"
            }

        all_queries = " ".join([turn['query'] for turn in self.conversation_history])
        intent_counts = {}
        for intent, keywords in QueryProcessor.INTENT_PATTERNS.items():
            count = sum(1 for kw in keywords if kw in all_queries.lower())
            if count > 0:
                intent_counts[intent] = count

        form_status = "not_triggered"
        if self.form_collector:
            form_status = self.form_collector.status.value
        elif self.user_declined_form:
            form_status = "declined"

        return {
            "total_turns": len(self.conversation_history),
            "message_count": self.message_count,
            "topics_discussed": list(intent_counts.keys()),
            "last_interaction": self.conversation_history[-1]['timestamp'],
            "form_status": form_status,
            "has_conversation_memory": len(self.conversation_history) > 0
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
    include_history: bool = True
) -> Dict[str, Any]:
    """
    Main chat interface with automatic form collection.

    Features:
    - Chat continuation with memory across messages
    - Automatic form collection trigger after N messages
    - Context-aware responses using conversation history

    Returns response with form_active flag to indicate if form collection is in progress
    """
    chatbot, session_id = _get_or_create_session(client_id, session_id)
    response = chatbot.chat(query, include_history=include_history)
    response['session_id'] = session_id
    response['has_conversation_memory'] = len(chatbot.conversation_history) > 0
    return response


def get_conversation_state(client_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Get conversation state including form status."""
    if session_id:
        chatbot, _ = _get_or_create_session(client_id, session_id)
        return chatbot.get_conversation_summary()
    return {
        "total_turns": 0,
        "topics_discussed": [],
        "last_interaction": None,
        "message": "No active session",
        "form_status": "not_triggered"
    }


def reset_conversation(client_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Reset conversation history and form state."""
    global _chatbot_sessions
    if session_id:
        session_key = f"{client_id}:{session_id}"
        with _session_lock:
            if session_key in _chatbot_sessions:
                _chatbot_sessions[session_key].clear_history()
                return {
                    "status": "success",
                    "message": f"History and form state cleared for {session_id}"
                }
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


def manually_trigger_form(
    client_id: str,
    session_id: str,
    form_type: str = "contact"
) -> Dict[str, Any]:
    """
    Manually trigger form collection (useful for testing or specific triggers)

    Args:
        client_id: Client identifier
        session_id: Session identifier
        form_type: 'contact' or 'demo_booking'
    """
    chatbot, _ = _get_or_create_session(client_id, session_id)

    if form_type == "demo_booking":
        template = FormTemplate.get_demo_booking_form()
    else:
        template = FormTemplate.get_contact_form()

    chatbot.form_collector = FormCollector(template)
    chatbot.form_triggered = True
    first_prompt = chatbot.form_collector.start()

    return {
        "status": "success",
        "message": first_prompt,
        "form_active": True,
        "form_type": form_type
    }


# Backward compatibility
UniversalRAGChatbot = InteractiveRAGChatbot
