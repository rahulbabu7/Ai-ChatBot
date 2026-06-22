# Smart Assist AI — Project Explained From Start to End

---

## What Is This Project?

Smart Assist AI is a **multi-tenant conversational AI platform**. In plain terms, it lets multiple businesses (called tenants) each get their own AI chatbot — all running on a single shared system. Each chatbot knows only its own company's information: their website, their PDFs, their custom Q&A. One tenant cannot see or access another tenant's data.

The problem it solves: most businesses want a chatbot that actually knows their products, policies, and services — not a generic AI that makes up answers. This platform ingests a company's real knowledge and uses it to answer questions accurately.

---

## Reading the Architecture Diagram — Left to Right

The diagram has three layers:

1. **Left side** — Who talks to the system (End User, Tenant Admin)
2. **Centre** — The brain of the system (FastAPI Backend + RAG Pipeline)
3. **Bottom** — Where data lives (MariaDB, ChromaDB, Groq API, Redis + Celery)

---

## Layer 1: The Two Types of Users

### End User
An end user is a visitor on a client company's website. They open a chat bubble and start asking questions like "What are your pricing plans?" or "How do I reset my password?"

They interact exclusively through the **Chatbot Widget**.

### Tenant Admin
A tenant admin is the business owner or manager who controls the chatbot. They log in to manage the chatbot's knowledge base, see what users are asking, view captured leads, and configure how the chatbot looks and behaves.

They interact through the **Admin Dashboard**.

---

## Layer 2: The Two React Frontends

Both frontends are built with **React + Vite**.

### Why React?
React is a component-based UI library. This means the UI is built from small reusable pieces (a chat bubble, a message list, a form). This makes it easy to manage complex UIs like a real-time chat window or a data table with pagination. React also handles state efficiently — when a new message arrives, only the chat window updates, not the whole page.

### Why Vite instead of Create React App?
Vite is a modern build tool that starts the development server almost instantly and reloads changes in under 100ms. Create React App (the old standard) can take several seconds to reload. For a project with two separate frontend apps, fast development feedback matters.

---

### The Chatbot Widget (React + Vite)

This is a lightweight React component that any client can embed into their website with a single script tag. It is authenticated using the tenant's `chatbot_key` — a secure token that tells the backend which company this widget belongs to.

**What it does:**
- Opens a chat window when the user clicks the chat bubble
- Sends the user's message to the FastAPI backend
- Shows a typing animation while the AI is thinking
- Displays the response along with source links (so the user can verify the answer)
- After a configurable number of messages, injects a lead-capture form asking for the user's name, email, and phone number

---

### The Admin Dashboard (React + Vite)

This is a full single-page application for the tenant administrator. It uses **React Router** for navigation between pages and **JWT tokens** stored in local storage for authentication.

**What it does:**
- Shows all chat conversations in real time (via WebSocket — no page refresh needed)
- Lets the admin upload PDFs, add Q&A pairs, and trigger website crawls
- Shows all captured leads and lets the admin export them as CSV
- Lets the admin change the chatbot's name, greeting, colour theme, and lead-form trigger threshold

---

## Layer 3: The FastAPI Backend — The Brain

The backend is built with **FastAPI** in **Python 3.11**. Everything flows through here.

### Why FastAPI?
FastAPI is an asynchronous web framework. "Asynchronous" means it can handle many requests at the same time without one request blocking another. For a chatbot platform where dozens of users might be chatting simultaneously, this is essential.

Other reasons:
- **Automatic validation** — It uses Pydantic models to validate every incoming request. If a message is too long or has a bad format, FastAPI rejects it before it even reaches the business logic.
- **Auto-generated API docs** — FastAPI generates a Swagger UI at `/docs` automatically, which made testing and integration much faster.
- **Type safety** — Python type hints throughout the code make bugs easier to catch early.

### What Are the Modules Inside FastAPI?

The diagram shows five modules: **Auth, Chat, Leads, WebSocket, Files**.

| Module | What It Does |
|---|---|
| **Auth** | Registers new tenant accounts, handles login, issues and validates JWT tokens |
| **Chat** | The main endpoint — receives user messages, runs security checks, triggers the RAG pipeline, returns the answer |
| **Leads** | Saves lead form submissions, returns lead records to the admin dashboard |
| **WebSocket** | Pushes real-time session updates to the admin dashboard without polling |
| **Files** | Handles PDF upload, Q&A management, website crawl triggers, source deletion |

---

## The RAG Pipeline — How the Chatbot Actually Answers

RAG stands for **Retrieval-Augmented Generation**. Instead of letting the AI make up answers from its training data (which leads to hallucination), we first find the most relevant pieces of the company's actual knowledge, then give those to the AI as context, and only then ask it to generate an answer.

The pipeline has four stages shown in the diagram: **BM25 → Semantic → RRF → Reranker**

---

### Stage 1: BM25 (Keyword Search)

**What it is:** BM25 (Best Match 25) is a classical keyword-based ranking algorithm. It looks at the exact words in the query and finds documents that contain those words, ranked by how often they appear and how rare they are across the whole collection.

**Why we included it:** Dense semantic search (explained next) is great for understanding meaning, but it struggles with exact matches. If a user types a specific product code like "MODEL-X2200" or a person's name, a semantic model might not rank the exact match at the top because it is looking at meaning, not spelling. BM25 catches these exact-match cases perfectly.

**Advantage:** Fast, requires no GPU, zero additional cost, and extremely reliable for specific terminology, product names, and numeric codes that organisations commonly use.

---

### Stage 2: Semantic Search (Dense Retrieval)

**What it is:** Each document chunk is converted into a 768-dimensional vector (a list of numbers) using a sentence-transformer model (`multi-qa-mpnet-base-dot-v1`). The user's query is converted to the same kind of vector. ChromaDB then finds the chunks whose vectors are closest to the query vector — meaning they are semantically similar even if they use different words.

**Why we included it:** Keyword search fails when the user asks a question using different words than the document uses. If the document says "cancellation policy" and the user asks "how do I stop my subscription?", BM25 finds nothing. Semantic search understands that both mean the same thing and returns the right chunk.

**Advantage:** Understands intent and meaning, handles paraphrasing, synonyms, and natural language questions that would confuse keyword search.

---

### Stage 3: RRF — Reciprocal Rank Fusion

**What it is:** RRF is a mathematical formula that merges two ranked lists (BM25 results and Semantic results) into one combined ranked list. Each document gets a score based on its position in each list: `score = 1 / (k + rank)` where k=60. Documents that appear near the top of both lists get the highest combined scores.

**Why we included it:** If we only used semantic search, we would miss exact-match queries. If we only used BM25, we would miss paraphrased queries. RRF lets us run both independently and combine their strengths. The formula is simple, fast, and has been shown in research to outperform more complex combination methods.

**Advantage:** No training required, no tuning of weights, works out of the box, and consistently produces better recall than either method alone.

---

### Stage 4: The Reranker (Cross-Encoder)

**What it is:** After RRF gives us the top-20 candidate documents, a cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) looks at each (query, document) pair together — not separately — and gives each pair a precise relevance score.

**Why we included it:** The semantic search model encodes the query and documents independently and measures vector similarity. This is fast but approximate. The cross-encoder reads the query and the document together in one pass, which is much more accurate because it can understand how the words in the query relate to specific words in the document. It is like the difference between matching resumes by job title vs. actually reading the resume alongside the job description.

**Advantage:** Significantly higher precision. The top-6 documents passed to the LLM are much more likely to actually answer the question, which means the LLM gives better answers and is less likely to say "I don't have information about that."

**Why only on top-20?** The cross-encoder is slower than BM25 or semantic search. Running it on all documents would be too slow. By first using BM25+Semantic+RRF to narrow down to 20 good candidates, we keep latency reasonable (0.4–0.8 seconds extra) while getting the precision benefit.

---

## Layer 4: The Data Layer

### MariaDB (with aiomysql)

**What it stores:** All structured data — tenant accounts, chat message history, lead records (name, email, phone), and session metadata.

**Why MariaDB:** It is a proven open-source relational database that is fully SQL-compatible with MySQL. It handles structured data with strong consistency guarantees, which is exactly what you want for user accounts and financial/contact information.

**Why aiomysql:** FastAPI is asynchronous. A normal MySQL driver would block the entire server while waiting for a database query to finish. `aiomysql` is the async version of the MySQL driver, so database queries run without blocking, allowing the server to handle other requests while waiting for the database.

---

### ChromaDB (Vector Database)

**What it stores:** The embedded document chunks — every piece of text from the crawled website, uploaded PDFs, and custom Q&A, converted into vectors and stored with metadata (source type, URL, page number).

**Why ChromaDB:** A regular database cannot search by meaning. ChromaDB is designed specifically for approximate nearest-neighbour search over vectors — it can find the 40 most similar chunks to a query vector in milliseconds, even with thousands of chunks stored. Each tenant gets their own collection (named by their client ID), ensuring complete data isolation.

**Why not FAISS or Pinecone:** FAISS is a library, not a database — it has no persistence layer and requires more code to manage. Pinecone is a managed cloud service that costs money per query. ChromaDB is open-source, runs locally or on a server, persists data to disk automatically, and supports metadata filtering which is essential for filtering by source type during deletion.

---

### Groq API (LLM)

**What it does:** After the RAG pipeline selects the top-6 most relevant document chunks, those chunks are placed into the system prompt as context. The Groq API then generates the final answer using a large language model (Llama or Mixtral, configurable via environment variable).

**Why Groq:** Groq runs LLMs on custom hardware (LPUs — Language Processing Units) that are dramatically faster than GPU-based inference. The Groq API consistently returned generated text in 0.5–1.2 seconds for a 100–300 token response. Comparable self-hosted GPU inference would be 3–5x slower. For a real-time chat application, every second of latency is noticeable to the user.

**Why not OpenAI:** Cost. Groq's inference is significantly cheaper for the volume of requests a multi-tenant platform generates. The model is also configurable, so the platform operator can switch models without changing any code.

---

### Redis + Celery (Task Queue)

**What it does:** Some operations take a long time — crawling a website can take minutes, and embedding hundreds of PDF pages takes time too. These cannot happen inside a web request (the user would be waiting). Instead, the FastAPI endpoint immediately returns a "task started" response, and the actual work is handed to a Celery worker running in the background.

**Why Celery:** Celery is Python's standard distributed task queue. It manages worker processes, retries failed tasks, and tracks task status. It handles all three long-running jobs: website crawling, document embedding, and the weekly scheduled recrawl.

**Why Redis:** Redis is the broker — it is the message bus that Celery uses to send tasks from the FastAPI process to the worker processes. It is also used as the result backend to store task completion status. Redis is chosen because it is extremely fast (in-memory), widely used with Celery, and easy to set up.

**Weekly Recrawl (Celery Beat):** A scheduler called Celery Beat runs every Sunday at 02:00 and automatically re-crawls every tenant's registered website to keep the knowledge base up to date without any manual action.

---

## End-to-End Flow: What Happens When a User Sends a Message

1. **User types a message** in the Chatbot Widget and hits send.
2. The widget sends a POST request to `/chat/{client_id}` on the FastAPI backend, authenticated with the `chatbot_key` header.
3. **FastAPI validates** the request (message length, format, session ID).
4. **SecurityMonitor** checks the message for prompt injection or suspicious patterns. If this is the third violation, the session is blocked.
5. **HybridRetriever** runs BM25 and semantic search in parallel, each returning 40 candidates.
6. **RRF** merges the two lists into a single ranked list of 20 documents.
7. **Cross-encoder** scores all 20 (query, document) pairs and picks the top 6.
8. **The top 6 chunks** are formatted into a context block and inserted into the system prompt.
9. **Groq API** generates a response grounded in those chunks.
10. **sanitise_llm_response()** strips any sensitive patterns from the output.
11. The response and source references are returned to the widget.
12. **MariaDB** records the full message exchange to the `chats` table.
13. **WebSocket** pushes a notification to any open Admin Dashboard, updating the session list in real time.

---

## Why This Architecture Works Well

| Problem | Solution |
|---|---|
| Generic AI makes up answers | RAG grounds every answer in the company's own verified documents |
| One system for many clients | Multi-tenant design with per-client ChromaDB collections and JWT-scoped API access |
| Keyword queries miss semantic matches | BM25 + Semantic hybrid retrieval covers both exact and meaning-based queries |
| Top retrieved chunks still not precise enough | Cross-encoder reranker re-scores pairs jointly for higher precision |
| Long-running tasks block the server | Celery + Redis moves crawling and embedding to background workers |
| Knowledge goes stale | Weekly auto-recrawl via Celery Beat keeps website content fresh |
| Chatbot leaks sensitive information | Output sanitisation, prompt hardening, SecurityMonitor, and rate limiting layer on top of each other |
