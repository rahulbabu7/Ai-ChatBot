"""
Enhanced Interactive RAG Chatbot System with Conversational Intelligence
Features: Clarifying questions, follow-ups, context gathering, and guided conversations
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

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "ChromaDatabase", "vector-database", "chroma_db"))
CLIENT_DATA_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "client_data"))

# Model configurations
EMBEDDING_MODEL = "multi-qa-mpnet-base-dot-v1"
GROQ_MODEL = settings.GROQ_MODEL
GROQ_API_KEY = settings.GROQ_API_KEY

# ──────────────────────────────────────────────────────────────────────────────
# Global Singletons & Session Management
# ──────────────────────────────────────────────────────────────────────────────

_embedder_lock = threading.Lock()
_groq_lock = threading.Lock()
_sentence_model: Optional[SentenceTransformer] = None
_groq_client: Optional[Groq] = None
_chroma_client: Optional[PersistentClient] = None
_chatbot_sessions: Dict[str, 'InteractiveRAGChatbot'] = {}
_session_lock = threading.Lock()


def _get_sentence_model() -> SentenceTransformer:
    """Lazy initialization of embedding model."""
    global _sentence_model
    if _sentence_model is None:
        with _embedder_lock:
            if _sentence_model is None:
                print("🔄 Loading embedding model...")
                _sentence_model = SentenceTransformer(EMBEDDING_MODEL)
    return _sentence_model


def _get_groq_client() -> Groq:
    """Lazy initialization of Groq client."""
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set in environment.")
        with _groq_lock:
            if _groq_client is None:
                _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _get_chroma() -> PersistentClient:
    """Lazy initialization of ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_DB_DIR, exist_ok=True)
        _chroma_client = PersistentClient(path=CHROMA_DB_DIR)
    return _chroma_client


# ──────────────────────────────────────────────────────────────────────────────
# Conversational Intelligence System
# ──────────────────────────────────────────────────────────────────────────────

class ConversationalIntelligence:
    """Analyzes queries and determines when to ask clarifying questions."""
    
    AMBIGUITY_PATTERNS = {
        'vague_pronouns': ['it', 'this', 'that', 'those', 'these', 'they'],
        'incomplete_questions': ['what about', 'tell me about', 'how about'],
        'multiple_topics': ['and', 'or', 'also'],
        'unclear_intent': ['information', 'details', 'stuff', 'things'],
    }
    
    CLARIFICATION_STRATEGIES = {
        'pricing': {
            'questions': [
                "Are you interested in pricing for a specific service or product?",
                "Would you like to know about regular pricing or any current promotions?",
            ],
            'keywords': ['price', 'cost', 'fee', 'expensive', 'cheap', 'rate']
        },
        'timing': {
            'questions': [
                "Which day of the week are you interested in?",
                "Is this for a specific date or in general?"
            ],
            'keywords': ['hour', 'time', 'schedule', 'when', 'open']
        },
        'location': {
            'questions': [
                "Are you looking for our physical address or directions?",
                "Which location are you interested in?"
            ],
            'keywords': ['where', 'location', 'address', 'find']
        },
        'process': {
            'questions': [
                "Do you need step-by-step instructions or just an overview?",
                "Are you at a specific step or starting from the beginning?"
            ],
            'keywords': ['how', 'apply', 'register', 'process', 'step']
        },
    }
    
    @staticmethod
    def analyze_query_completeness(query: str) -> Dict[str, Any]:
        """Analyze if query needs clarification."""
        query_lower = query.lower()
        words = query_lower.split()
        
        analysis = {
            'is_complete': True,
            'issues': [],
            'suggested_clarifications': [],
            'confidence': 1.0
        }
        
        if len(words) < 3:
            analysis['is_complete'] = False
            analysis['issues'].append('too_short')
            analysis['confidence'] *= 0.6
        
        vague_pronouns = [w for w in words if w in ConversationalIntelligence.AMBIGUITY_PATTERNS['vague_pronouns']]
        if vague_pronouns and len(words) < 8:
            analysis['is_complete'] = False
            analysis['issues'].append('vague_reference')
            analysis['confidence'] *= 0.7
        
        for pattern in ConversationalIntelligence.AMBIGUITY_PATTERNS['incomplete_questions']:
            if pattern in query_lower:
                analysis['is_complete'] = False
                analysis['issues'].append('incomplete_question')
                analysis['confidence'] *= 0.5
                break
        
        for topic, data in ConversationalIntelligence.CLARIFICATION_STRATEGIES.items():
            if any(kw in query_lower for kw in data['keywords']):
                if len(words) < 6 or any(issue in analysis['issues'] for issue in ['too_short', 'vague_reference']):
                    analysis['suggested_clarifications'].extend(data['questions'][:1])
        
        return analysis
    
    @staticmethod
    def detect_follow_up_opportunity(query: str, answer: str, documents: List[Dict[str, Any]]) -> Optional[str]:
        """Detect if we should suggest a follow-up question."""
        query_lower = query.lower()
        answer_lower = answer.lower()
        
        # Don't suggest follow-ups if user is taking action
        action_keywords = ['book', 'schedule', 'register', 'sign up', 'demo', 'appointment', 'buy', 'purchase']
        if any(keyword in query_lower for keyword in action_keywords):
            return None
        
        if 'option' in answer_lower or 'either' in answer_lower:
            return "Would you like more details about any specific option?"
        
        if any(word in answer_lower for word in ['various', 'different', 'multiple', 'several']):
            return "Would you like me to explain any of these in more detail?"
        
        if any(word in answer_lower for word in ['require', 'need to', 'must', 'step']):
            return "Would you like me to walk you through these in detail?"
        
        return None
    
    @staticmethod
    def generate_probing_questions(query: str, context: str, intent: str) -> List[str]:
        """Generate smart, context-aware probing questions."""
        questions = []
        context_lower = context.lower()
        query_lower = query.lower()
        
        # Don't suggest if user is taking action
        action_keywords = ['book', 'schedule', 'register', 'sign up', 'demo', 'appointment', 'buy', 'purchase', 'contact', 'call', 'email']
        if any(keyword in query_lower for keyword in action_keywords):
            return []
        
        # Don't suggest info that was just discussed
        recent_topics = ['hour', 'schedule', 'location', 'address', 'contact', 'price', 'cost', 'phone', 'email']
        if any(topic in query_lower for topic in recent_topics):
            return []
        
        # Check available context
        has_pricing = any(word in context_lower for word in ['price', 'cost', '$', 'fee', 'payment'])
        has_timing = any(word in context_lower for word in ['hour', 'schedule', 'monday', 'tuesday'])
        has_location = any(word in context_lower for word in ['address', 'location', 'street', 'building'])
        
        # Only suggest if contextually relevant
        if has_pricing and intent not in ['pricing', 'contact', 'timing'] and 'pricing' not in query_lower:
            if any(word in query_lower for word in ['service', 'product', 'offer', 'what', 'about', 'feature']):
                questions.append("Would you like to know about pricing?")
        
        if has_timing and intent != 'timing' and 'hour' not in query_lower:
            if any(word in query_lower for word in ['visit', 'come', 'available', 'when']):
                questions.append("Would you like to know about our hours?")
        
        if has_location and intent not in ['contact', 'location'] and 'location' not in query_lower:
            if any(word in query_lower for word in ['visit', 'come', 'see', 'where']):
                questions.append("Need our location information?")
        
        return questions[:1]  # Max 1 suggestion


# ──────────────────────────────────────────────────────────────────────────────
# Query Processing
# ──────────────────────────────────────────────────────────────────────────────

class QueryProcessor:
    """Advanced query processing with intent detection."""

    INTENT_PATTERNS = {
        'contact': ['contact', 'phone', 'email', 'reach', 'call', 'address', 'location'],
        'pricing': ['price', 'cost', 'fee', 'charge', 'expensive', 'cheap', 'rate'],
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
    """Interactive RAG chatbot with conversational intelligence."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.retriever = HybridRetriever(client_id)
        self.groq_client = _get_groq_client()
        self.conversation_history = []
        self.conversational_ai = ConversationalIntelligence()
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

    def _build_context_string(self, documents: List[Dict[str, Any]], max_tokens: int = 3000) -> str:
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4
        for doc in documents:
            content = doc['content'].strip()
            meta = doc['metadata']
            source_info = ""
            if meta.get('source') == 'crawl':
                source_info = f"[Source: {meta.get('title', 'Web Page')}]"
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

    def _create_interactive_prompt(self, query: str, context: str, intent: str, is_clarification_needed: bool = False) -> str:
        tone = self.client_metadata.get("tone", "professional and helpful")
        business_type = self.client_metadata.get("business_type", "organization")
        
        interactive_instruction = """
6. Be conversational and natural - suggest related questions if relevant.
7. If the question is vague, briefly answer what you can then ask for clarification.""" if is_clarification_needed else """
6. Be conversational and helpful in your responses."""
        
        return f"""You are an intelligent assistant for a {business_type}. Provide accurate information AND engage naturally with users.

CONTEXT:
{context}

GUIDELINES:
1. Answer using the context above
2. Be specific with details (numbers, dates, names)
3. Use a {tone} tone
4. Keep answers concise (2-4 sentences) unless more detail is needed
5. If context is incomplete, provide what you can
{interactive_instruction}

USER QUESTION: {query}

ANSWER:"""

    def chat(self, query: str, include_history: bool = True, max_history: int = 3, enable_clarifications: bool = True) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"answer": "I'm here to help! What would you like to know?", "confidence": "none", "sources": [], "type": "prompt", "probing_questions": []}
        
        start_time = datetime.now()
        needs_clarification = False
        clarification_questions = []
        
        if enable_clarifications:
            completeness = self.conversational_ai.analyze_query_completeness(query)
            if not completeness['is_complete'] and completeness['confidence'] < 0.7:
                needs_clarification = True
                clarification_questions = completeness['suggested_clarifications']
        
        # Check custom Q&A
        custom_match = self.retriever.match_custom_qa(query)
        if custom_match and custom_match['confidence'] == 'high':
            follow_up = self.conversational_ai.detect_follow_up_opportunity(query, custom_match['answer'], [])
            response = {
                "answer": custom_match['answer'],
                "confidence": custom_match['confidence'],
                "sources": [{"type": "custom_qa", "title": "Official Q&A"}],
                "type": "custom_qa",
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "follow_up_question": follow_up,
                "probing_questions": [],
                "clarification_questions": []
            }
            self._update_history(query, response['answer'])
            return response
        
        # Retrieve documents
        intent = self.retriever.query_processor.detect_intent(query)
        documents = self.retriever.retrieve_documents(query, top_k=12)
        
        if not documents:
            return {
                "answer": "I couldn't find specific information about that. Could you rephrase or provide more details?",
                "confidence": "none",
                "sources": [],
                "type": "no_results",
                "clarification_questions": ["What specific information are you looking for?"],
                "probing_questions": [],
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
        
        # Build context
        context = self._build_context_string(documents)
        if include_history and self.conversation_history:
            history_context = self._format_history(max_history)
            context = f"{history_context}\n\n---\n\nCURRENT CONTEXT:\n{context}"
        
        # Generate probing questions
        probing_questions = self.conversational_ai.generate_probing_questions(query, context, intent)
        
        # Generate response
        prompt = self._create_interactive_prompt(query, context, intent, needs_clarification)
        try:
            completion = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
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
                "probing_questions": [],
                "clarification_questions": [],
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
        
        confidence = self._estimate_confidence(documents, answer)
        follow_up = self.conversational_ai.detect_follow_up_opportunity(query, answer, documents)
        
        sources = []
        for doc in documents[:5]:
            meta = doc['metadata']
            source_info = {"score": doc['score']}
            if meta.get('source') == 'crawl':
                source_info.update({"type": "webpage", "title": meta.get('title', 'Web Page'), "url": meta.get('url', '')})
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
            "clarification_questions": clarification_questions,
            "follow_up_question": follow_up,
            "probing_questions": probing_questions,
            "metadata": {"intent": intent, "num_documents": len(documents)}
        }
        
        self._update_history(query, answer)
        return response

    def _estimate_confidence(self, documents: List[Dict[str, Any]], answer: str) -> str:
        if not documents:
            return "none"
        avg_score = sum(d['score'] for d in documents[:5]) / min(len(documents), 5)
        uncertainty_phrases = ["don't have", "not sure", "unclear", "may vary", "recommend contacting"]
        has_uncertainty = any(phrase in answer.lower() for phrase in uncertainty_phrases)
        asks_clarification = "?" in answer and any(word in answer.lower() for word in ["which", "what", "would you"])
        if asks_clarification:
            return "medium"
        elif has_uncertainty:
            return "low"
        elif avg_score >= 0.75 and len(documents) >= 3:
            return "high"
        elif avg_score >= 0.60:
            return "medium"
        return "low"

    def _update_history(self, query: str, answer: str, max_history: int = 10):
        self.conversation_history.append({"query": query, "answer": answer, "timestamp": datetime.now().isoformat()})
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]

    def _format_history(self, max_turns: int = 3) -> str:
        if not self.conversation_history:
            return ""
        recent = self.conversation_history[-max_turns:]
        history_lines = ["RECENT CONVERSATION:"]
        for turn in recent:
            history_lines.append(f"User: {turn['query']}")
            history_lines.append(f"Assistant: {turn['answer']}\n")
        return "\n".join(history_lines)

    def clear_history(self):
        self.conversation_history = []

    def get_conversation_summary(self) -> Dict[str, Any]:
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
    global _chatbot_sessions
    if session_id is None:
        session_id = f"{client_id}_{datetime.now().timestamp()}"
    session_key = f"{client_id}:{session_id}"
    with _session_lock:
        if session_key not in _chatbot_sessions:
            _chatbot_sessions[session_key] = InteractiveRAGChatbot(client_id)
        return _chatbot_sessions[session_key], session_id


def chat_with_model(client_id: str, query: str, session_id: Optional[str] = None, include_history: bool = True, enable_clarifications: bool = True) -> Dict[str, Any]:
    chatbot, session_id = _get_or_create_session(client_id, session_id)
    response = chatbot.chat(query, include_history=include_history, enable_clarifications=enable_clarifications)
    response['session_id'] = session_id
    return response


def explain_context(client_id: str, query: str) -> Dict[str, Any]:
    retriever = HybridRetriever(client_id)
    conv_ai = ConversationalIntelligence()
    documents = retriever.retrieve_documents(query)
    intent = retriever.query_processor.detect_intent(query)
    completeness = conv_ai.analyze_query_completeness(query)
    return {
        "query": query,
        "intent": intent,
        "query_analysis": completeness,
        "num_documents": len(documents),
        "documents": [{"content": doc['content'][:200] + "...", "score": doc['score'], "metadata": doc['metadata']} for doc in documents]
    }


def get_conversation_state(client_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    if session_id:
        chatbot, _ = _get_or_create_session(client_id, session_id)
        return chatbot.get_conversation_summary()
    return {"total_turns": 0, "topics_discussed": [], "last_interaction": None, "message": "No active session"}


def reset_conversation(client_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    global _chatbot_sessions
    if session_id:
        session_key = f"{client_id}:{session_id}"
        with _session_lock:
            if session_key in _chatbot_sessions:
                _chatbot_sessions[session_key].clear_history()
                return {"status": "success", "message": f"History cleared for {session_id}"}
    return {"status": "success", "message": "No active session"}


def clear_session(client_id: str, session_id: str) -> Dict[str, Any]:
    global _chatbot_sessions
    session_key = f"{client_id}:{session_id}"
    with _session_lock:
        if session_key in _chatbot_sessions:
            del _chatbot_sessions[session_key]
            return {"status": "success", "message": f"Session {session_id} removed"}
    return {"status": "not_found", "message": "Session not found"}


def cleanup_old_sessions(max_age_hours: int = 24) -> Dict[str, Any]:
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
    Debug function to see retrieved context and conversational analysis.

    Returns:
        Retrieved documents with scores, metadata, and conversational intelligence analysis
    """
    retriever = HybridRetriever(client_id)
    conv_ai = ConversationalIntelligence()
    
    documents = retriever.retrieve_documents(query)
    intent = retriever.query_processor.detect_intent(query)
    completeness = conv_ai.analyze_query_completeness(query)

    return {
        "query": query,
        "intent": intent,
        "query_analysis": completeness,
        "num_documents": len(documents),
        "documents": [
            {
                "content": doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                "score": doc['score'],
                "metadata": doc['metadata']
            }
            for doc in documents
        ]
    }


# def get_conversation_state(client_id: str) -> Dict[str, Any]:
#     """
#     Get current conversation state and history summary.

#     Returns:
#         Conversation summary with topics, turns, and statistics
#     """
#     chatbot = InteractiveRAGChatbot(client_id)
#     return chatbot.get_conversation_summary()


# def reset_conversation(client_id: str) -> Dict[str, Any]:
#     """
#     Reset conversation history for a client.

#     Returns:
#         Confirmation message
#     """
#     chatbot = InteractiveRAGChatbot(client_id)
#     chatbot.clear_history()
#     return {
#         "status": "success",
#         "message": "Conversation history cleared"
#     }


# ──────────────────────────────────────────────────────────────────────────────
# Backward Compatibility
# ──────────────────────────────────────────────────────────────────────────────

# Alias for backward compatibility with existing imports
UniversalRAGChatbot = InteractiveRAGChatbot