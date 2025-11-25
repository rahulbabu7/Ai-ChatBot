"""
Enhanced Universal RAG Chatbot System with LangChain
Supports any website with advanced semantic understanding and context-aware responses
"""

import os
import json
import threading
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from backend.config import settings
from groq import Groq
from sentence_transformers import SentenceTransformer
from chromadb import PersistentClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "ChromaDatabase", "vector-database", "chroma_db"))
CLIENT_DATA_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "client_data"))

# Model configurations
EMBEDDING_MODEL = "multi-qa-mpnet-base-dot-v1"  # 768-dim, optimized for Q&A
GROQ_MODEL = settings.GROQ_MODEL
GROQ_API_KEY = settings.GROQ_API_KEY

# ──────────────────────────────────────────────────────────────────────────────
# Global Singletons
# ──────────────────────────────────────────────────────────────────────────────

_embedder_lock = threading.Lock()
_groq_lock = threading.Lock()
_sentence_model: Optional[SentenceTransformer] = None
_groq_client: Optional[Groq] = None
_chroma_client: Optional[PersistentClient] = None


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
# Advanced Query Processing
# ──────────────────────────────────────────────────────────────────────────────

class QueryProcessor:
    """Advanced query processing with intent detection and expansion."""

    # Domain-agnostic query expansion patterns
    EXPANSION_PATTERNS = {
        # Time-related
        'hours': 'hours time schedule timing open close',
        'timing': 'hours time schedule timing open close',
        'schedule': 'hours time schedule timing timetable',

        # Location/Contact
        'location': 'location address where find situated contact',
        'address': 'location address where find situated',
        'contact': 'contact phone email reach call message',
        'phone': 'contact phone number call telephone',
        'email': 'contact email address mail',

        # Cost/Pricing
        'price': 'price cost fee charge rate pricing amount',
        'cost': 'price cost fee charge rate pricing',
        'fee': 'price cost fee charge rate payment',

        # Process/How-to
        'how': 'how process steps procedure method way',
        'process': 'how process steps procedure method requirements',
        'apply': 'apply application process registration enroll signup',
        'register': 'register registration enroll enrollment signup',

        # Information requests
        'what': 'what description information details about',
        'about': 'about information details description overview',
        'details': 'details information specifics particulars',

        # Availability
        'available': 'available availability offered provide',
        'offer': 'offer provide available services products',
    }

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
        """Detect query intent for better retrieval."""
        query_lower = query.lower()
        intent_scores = {}

        for intent, keywords in QueryProcessor.INTENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                intent_scores[intent] = score

        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        return 'general'

    @staticmethod
    def expand_query(query: str, max_expansions: int = 3) -> str:
        """Expand query with related terms for better retrieval."""
        query_lower = query.lower()
        query_words = query_lower.split()
        expanded_terms = set()

        for word in query_words:
            for key, expansion in QueryProcessor.EXPANSION_PATTERNS.items():
                if key in word or word in key:
                    # Add expansion terms
                    terms = expansion.split()
                    expanded_terms.update(terms[:max_expansions])

        # Remove terms already in query
        new_terms = expanded_terms - set(query_words)

        if new_terms:
            # Limit to most relevant expansions
            return f"{query} {' '.join(list(new_terms)[:max_expansions])}"
        return query

    @staticmethod
    def preprocess(query: str) -> str:
        """Clean and normalize query."""
        import re
        # Remove excessive punctuation but keep meaningful ones
        query = re.sub(r'[^\w\s?!.,\-\'"]', '', query)
        # Normalize whitespace
        query = ' '.join(query.split())
        return query.strip()


# ──────────────────────────────────────────────────────────────────────────────
# Hybrid Retrieval System
# ──────────────────────────────────────────────────────────────────────────────

class HybridRetriever:
    """
    Advanced hybrid retrieval combining:
    1. Dense vector search (semantic similarity)
    2. Custom Q&A matching
    3. Keyword boosting
    4. Multi-query retrieval
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.embedder = _get_sentence_model()
        self.collection = self._get_collection()
        self.custom_qa = self._load_custom_qa()
        self.query_processor = QueryProcessor()

    def _get_collection(self):
        """Get or create ChromaDB collection for client."""
        try:
            chroma = _get_chroma()
            return chroma.get_collection(self.client_id.lower())
        except Exception as e:
            print(f"⚠️ Collection not found for {self.client_id}: {e}")
            return None

    def _load_custom_qa(self) -> List[Dict[str, Any]]:
        """Load and preprocess custom Q&A pairs."""
        qa_path = os.path.join(CLIENT_DATA_DIR, self.client_id, "custom_qa.json")

        if not os.path.exists(qa_path):
            return []

        try:
            with open(qa_path, 'r', encoding='utf-8') as f:
                qa_data = json.load(f)

            # Normalize and embed
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
        """Match against custom Q&A with semantic similarity."""
        if not self.custom_qa:
            return None

        query_emb = self.embedder.encode(query)
        best_match = {'score': -1.0, 'answer': None, 'question': None, 'metadata': {}}

        for qa in self.custom_qa:
            for q_text, emb in zip(qa["questions"], qa["embeddings"]):
                # Compute cosine similarity
                from sentence_transformers import util
                similarity = util.cos_sim(query_emb, emb).item()

                # Keyword overlap boost
                query_words = set(query.lower().split())
                qa_words = set(q_text.lower().split())
                overlap = len(query_words & qa_words) / max(len(query_words), len(qa_words))

                # Combined score (85% semantic, 15% keyword)
                combined_score = 0.85 * similarity + 0.15 * overlap

                if combined_score > best_match['score']:
                    best_match = {
                        'score': combined_score,
                        'answer': qa["answer"],
                        'question': q_text,
                        'metadata': qa.get("metadata", {})
                    }

        # Dynamic threshold based on query characteristics
        query_length = len(query.split())
        adjusted_threshold = threshold + (0.05 if query_length < 5 else 0)

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

    def retrieve_documents(
        self,
        query: str,
        top_k: int = 15,
        diversity_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Advanced retrieval with multi-query and diversity.

        Args:
            query: User query
            top_k: Number of documents to retrieve
            diversity_weight: Balance between relevance and diversity (0-1)
        """
        if not self.collection:
            return []

        # Preprocess query
        clean_query = self.query_processor.preprocess(query)
        intent = self.query_processor.detect_intent(clean_query)

        # Generate query variations
        queries = [
            clean_query,
            self.query_processor.expand_query(clean_query)
        ]

        # Add intent-specific query if detected
        if intent != 'general':
            queries.append(f"{clean_query} {intent}")

        all_results = []
        seen_ids = set()

        # Retrieve with each query variation
        for q in queries[:2]:  # Limit to 2 variations to avoid redundancy
            try:
                q_emb = self.embedder.encode(q)
                results = self.collection.query(
                    query_embeddings=[q_emb.tolist()],
                    n_results=min(top_k, 20)
                )

                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
                ids = results.get("ids", [[]])[0]

                for doc, meta, dist, doc_id in zip(docs, metas, distances, ids):
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        # Convert distance to similarity score (1 - normalized distance)
                        similarity = 1 / (1 + dist)
                        all_results.append({
                            'content': doc,
                            'metadata': meta,
                            'score': similarity,
                            'id': doc_id
                        })

            except Exception as e:
                print(f"⚠️ Retrieval error for query '{q}': {e}")
                continue

        if not all_results:
            return []

        # Diversify results using MMR-like approach
        if diversity_weight > 0 and len(all_results) > 1:
            all_results = self._diversify_results(all_results, top_k, diversity_weight)
        else:
            # Sort by score and take top_k
            all_results.sort(key=lambda x: x['score'], reverse=True)
            all_results = all_results[:top_k]

        return all_results

    def _diversify_results(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
        diversity_weight: float
    ) -> List[Dict[str, Any]]:
        """Apply MMR-like diversification to reduce redundancy."""
        if len(results) <= top_k:
            return results

        # Sort by initial relevance
        results.sort(key=lambda x: x['score'], reverse=True)

        selected = [results[0]]  # Always take the most relevant
        remaining = results[1:]

        while len(selected) < top_k and remaining:
            best_idx = 0
            best_score = -1

            for idx, candidate in enumerate(remaining):
                # Relevance score
                relevance = candidate['score']

                # Diversity score (minimum similarity to selected docs)
                diversity = 1.0
                for selected_doc in selected:
                    similarity = self._compute_text_similarity(
                        candidate['content'],
                        selected_doc['content']
                    )
                    diversity = min(diversity, 1 - similarity)

                # Combined score
                mmr_score = (1 - diversity_weight) * relevance + diversity_weight * diversity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            selected.append(remaining.pop(best_idx))

        return selected

    @staticmethod
    def _compute_text_similarity(text1: str, text2: str) -> float:
        """Fast text similarity using token overlap (Jaccard)."""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# LangChain RAG Pipeline
# ──────────────────────────────────────────────────────────────────────────────

class UniversalRAGChatbot:
    """
    Universal RAG chatbot with LangChain integration.
    Works for any website with advanced context understanding.
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.retriever = HybridRetriever(client_id)
        self.groq_client = _get_groq_client()
        self.conversation_history = []

        # Load client metadata for context
        self.client_metadata = self._load_client_metadata()

    def _load_client_metadata(self) -> Dict[str, Any]:
        """Load client-specific metadata for better responses."""
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
            "tone": "professional and helpful"
        }

    def _build_context_string(self, documents: List[Dict[str, Any]], max_tokens: int = 3000) -> str:
        """Build context string from retrieved documents with smart truncation."""
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough estimate: 1 token ≈ 4 chars

        for i, doc in enumerate(documents, 1):
            content = doc['content'].strip()
            meta = doc['metadata']

            # Add source attribution
            source_info = ""
            if meta.get('source') == 'crawl':
                source_info = f"[Source: {meta.get('title', 'Web Page')}]"
            elif meta.get('source') == 'pdf':
                source_info = f"[Source: {meta.get('filename', 'PDF Document')}]"
            elif meta.get('source') == 'qa':
                source_info = "[Source: Official Q&A]"

            doc_text = f"{source_info}\n{content}\n"

            if total_chars + len(doc_text) > max_chars:
                # Truncate if needed
                remaining = max_chars - total_chars
                if remaining > 200:
                    doc_text = doc_text[:remaining] + "...\n"
                    context_parts.append(doc_text)
                break

            context_parts.append(doc_text)
            total_chars += len(doc_text)

        return "\n---\n".join(context_parts)

    def _create_prompt(self, query: str, context: str, intent: str) -> str:
        """Create enhanced prompt with intent awareness."""

        domain = self.client_metadata.get("domain", "general")
        business_type = self.client_metadata.get("business_type", "organization")
        tone = self.client_metadata.get("tone", "professional and helpful")

        # Intent-specific instructions
        intent_instructions = {
            'contact': "Pay special attention to contact information like phone numbers, emails, addresses, and hours.",
            'pricing': "Focus on pricing details, costs, fees, and payment information.",
            'timing': "Emphasize schedules, hours, timings, and availability.",
            'process': "Explain step-by-step processes and requirements clearly.",
            'comparison': "Provide balanced comparisons highlighting key differences.",
            'availability': "Clearly state what is available and any limitations."
        }

        intent_instruction = intent_instructions.get(intent, "")

        prompt = f"""You are an intelligent assistant for a {business_type}. Your role is to provide accurate, helpful information based solely on the provided context.

CONTEXT INFORMATION:
{context}

RESPONSE GUIDELINES:
1. Answer ONLY using information from the context above
2. Be specific and include relevant details (numbers, dates, names, requirements)
3. Use a {tone} tone
4. If the context doesn't contain the answer, say: "I don't have that specific information available. I recommend contacting us directly for more details."
5. Keep answers concise (2-4 sentences) unless more detail is clearly needed
6. {intent_instruction}
7. If the context has partial information, provide what you can and acknowledge what's missing
8. Never make up or assume information not in the context

USER QUESTION: {query}

ANSWER:"""

        return prompt

    def chat(
        self,
        query: str,
        include_history: bool = False,
        max_history: int = 3
    ) -> Dict[str, Any]:
        """
        Main chat interface with enhanced context awareness.

        Args:
            query: User question
            include_history: Whether to include conversation history
            max_history: Maximum conversation turns to include

        Returns:
            Response dictionary with answer, sources, and metadata
        """
        if not query or not query.strip():
            return {
                "answer": "Please provide a question.",
                "confidence": "none",
                "sources": [],
                "type": "error"
            }

        start_time = datetime.now()

        # Step 1: Check custom Q&A first (highest priority)
        custom_match = self.retriever.match_custom_qa(query)
        if custom_match:
            response = {
                "answer": custom_match['answer'],
                "confidence": custom_match['confidence'],
                "sources": [{
                    "type": "custom_qa",
                    "title": "Official Q&A",
                    "matched_question": custom_match['matched_question']
                }],
                "type": "custom_qa",
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "metadata": {
                    "match_score": custom_match['score'],
                    "intent": "direct_match"
                }
            }

            # Add to conversation history
            self._update_history(query, response['answer'])
            return response

        # Step 2: Retrieve relevant documents
        intent = self.retriever.query_processor.detect_intent(query)
        documents = self.retriever.retrieve_documents(query, top_k=12)

        if not documents:
            return {
                "answer": "I couldn't find relevant information to answer your question. Please try rephrasing or contact us directly for assistance.",
                "confidence": "none",
                "sources": [],
                "type": "no_results",
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

        # Step 3: Build context with history if requested
        context = self._build_context_string(documents)

        if include_history and self.conversation_history:
            history_context = self._format_history(max_history)
            context = f"{history_context}\n\n---\n\nCURRENT CONTEXT:\n{context}"

        # Step 4: Generate response using LLM
        prompt = self._create_prompt(query, context, intent)

        try:
            completion = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Lower for more factual responses
                top_p=0.9,
                max_tokens=500,
                stream=False
            )

            answer = completion.choices[0].message.content.strip()

        except Exception as e:
            return {
                "answer": f"I encountered an error generating a response. Please try again.",
                "confidence": "error",
                "sources": [],
                "type": "llm_error",
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

        # Step 5: Estimate confidence
        confidence = self._estimate_confidence(documents, answer)

        # Format sources
        sources = []
        for doc in documents[:5]:  # Top 5 sources
            meta = doc['metadata']
            source_info = {"score": doc['score']}

            if meta.get('source') == 'crawl':
                source_info.update({
                    "type": "webpage",
                    "title": meta.get('title', 'Web Page'),
                    "url": meta.get('url', '')
                })
            elif meta.get('source') == 'pdf':
                source_info.update({
                    "type": "document",
                    "title": meta.get('filename', 'PDF Document')
                })
            elif meta.get('source') == 'qa':
                source_info.update({
                    "type": "qa",
                    "title": "Custom Q&A"
                })

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
                "context_length": len(context)
            }
        }

        # Update conversation history
        self._update_history(query, answer)

        return response

    def _estimate_confidence(self, documents: List[Dict[str, Any]], answer: str) -> str:
        """Estimate confidence based on retrieval quality and answer characteristics."""
        if not documents:
            return "none"

        # Average document score
        avg_score = sum(d['score'] for d in documents[:5]) / min(len(documents), 5)

        # Check if answer indicates uncertainty
        uncertainty_phrases = [
            "don't have", "not sure", "unclear", "may vary",
            "recommend contacting", "please contact", "i couldn't find"
        ]
        has_uncertainty = any(phrase in answer.lower() for phrase in uncertainty_phrases)

        # Determine confidence
        if has_uncertainty:
            return "low"
        elif avg_score >= 0.75 and len(documents) >= 3:
            return "high"
        elif avg_score >= 0.60 or len(documents) >= 2:
            return "medium"
        else:
            return "low"

    def _update_history(self, query: str, answer: str, max_history: int = 10):
        """Update conversation history."""
        self.conversation_history.append({
            "query": query,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only recent history
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]

    def _format_history(self, max_turns: int = 3) -> str:
        """Format recent conversation history for context."""
        if not self.conversation_history:
            return ""

        recent = self.conversation_history[-max_turns:]
        history_lines = ["RECENT CONVERSATION HISTORY:"]

        for turn in recent:
            history_lines.append(f"User: {turn['query']}")
            history_lines.append(f"Assistant: {turn['answer']}\n")

        return "\n".join(history_lines)

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def chat_with_model(
    client_id: str,
    query: str,
    include_history: bool = False
) -> Dict[str, Any]:
    """
    Enhanced universal chat interface.

    Args:
        client_id: Client identifier
        query: User question
        include_history: Whether to include conversation context

    Returns:
        Comprehensive response with answer, confidence, and sources
    """
    chatbot = UniversalRAGChatbot(client_id)
    return chatbot.chat(query, include_history=include_history)


def explain_context(client_id: str, query: str) -> Dict[str, Any]:
    """
    Debug function to see retrieved context.

    Returns:
        Retrieved documents with scores and metadata
    """
    retriever = HybridRetriever(client_id)
    documents = retriever.retrieve_documents(query)

    return {
        "query": query,
        "intent": retriever.query_processor.detect_intent(query),
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
