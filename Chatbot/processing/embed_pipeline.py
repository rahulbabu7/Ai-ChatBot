# import os
# import json
# import re
# import sys
# from sentence_transformers import SentenceTransformer
# import chromadb
# from nltk.tokenize import sent_tokenize

# # ---------- Helpers ----------
# def clean_text(text: str) -> str:
#     text = re.sub(r'\S+@\S+', '', text)   # remove emails
#     text = re.sub(r'\d{10,}', '', text)   # remove long numbers
#     text = re.sub(r'\s+', ' ', text)      # normalize whitespace
#     return text.strip()

# def chunk_text(text: str, chunk_size=500, overlap=50):
#     sentences = sent_tokenize(text)
#     chunks, current, total_words = [], [], 0
#     for sentence in sentences:
#         words = sentence.split()
#         if total_words + len(words) > chunk_size:
#             chunks.append(" ".join(current))
#             current = current[-overlap:]
#             total_words = sum(len(s.split()) for s in current)
#         current.append(sentence)
#         total_words += len(words)
#     if current:
#         chunks.append(" ".join(current))
#     return chunks

# # ---------- Pipeline ----------
# def run_pipeline(client_id: str):
#     base_dir = os.path.join("backend", "client_data", client_id)
#     input_path = os.path.join(base_dir, "website_content.json")
#     chunk_path = os.path.join(base_dir, "website_chunks.json")
#     embed_path = os.path.join(base_dir, "website_embeddings.json")
#     qa_path = os.path.join(base_dir, "custom_qa.json")
#     chroma_dir = os.path.join("chatbot", "vector-database", "chroma_db")

#     if not os.path.exists(input_path):
#         raise FileNotFoundError(f"❌ Crawled data not found for {client_id}: {input_path}")

#     # 1️⃣ Load crawled website data
#     with open(input_path, "r", encoding="utf-8") as f:
#         pages = json.load(f)

#     chunks = []
#     for page in pages:
#         url, title, content = page.get("url"), page.get("title", ""), page.get("content", "")
#         if not content.strip():
#             continue
#         text = clean_text(content)
#         for c in chunk_text(text):
#             chunks.append({"url": url, "title": title, "content": c})

#     # 2️⃣ Add custom Q&A if available
#     if os.path.exists(qa_path):
#         with open(qa_path, "r", encoding="utf-8") as f:
#             qa_pairs = json.load(f)
#         for qa in qa_pairs:
#             q, a = qa.get("question"), qa.get("answer")
#             if q and a:
#                 chunks.append({
#                     "url": "custom_qa",
#                     "title": "Q&A",
#                     "content": f"Q: {q}\nA: {a}"
#                 })
#         print(f"➕ Added {len(qa_pairs)} custom Q&A entries")

#     with open(chunk_path, "w", encoding="utf-8") as f:
#         json.dump(chunks, f, indent=2, ensure_ascii=False)
#     print(f"✅ Saved {len(chunks)} chunks to {chunk_path}")

#     # 3️⃣ Generate embeddings
#     model = SentenceTransformer("all-MiniLM-L6-v2")
#     embeddings = model.encode([c["content"] for c in chunks], show_progress_bar=True)
#     for c, e in zip(chunks, embeddings):
#         c["embedding"] = e.tolist()

#     with open(embed_path, "w", encoding="utf-8") as f:
#         json.dump(chunks, f, indent=2, ensure_ascii=False)
#     print(f"✅ Saved embeddings for {len(chunks)} chunks to {embed_path}")

#     # 4️⃣ Store in ChromaDB
#     try:
#         client = chromadb.PersistentClient(path=chroma_dir)
#         coll = client.get_or_create_collection(name=client_id.lower())

#         ids = [f"{client_id}_chunk_{i}" for i in range(len(chunks))]
#         coll.add(
#             documents=[c["content"] for c in chunks],
#             metadatas=[{"url": c["url"], "title": c["title"]} for c in chunks],
#             ids=ids,
#             embeddings=[c["embedding"] for c in chunks],
#         )
#         print(f"🎉 Ingested {len(chunks)} chunks into Chroma collection '{client_id.lower()}'")
#     except Exception as e:
#         raise RuntimeError(f"❌ Failed to store in ChromaDB: {e}")

# # ---------- Entrypoint ----------
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python embed_pipeline.py <client_id>")
#         sys.exit(1)
#     run_pipeline(sys.argv[1])

import os
import json
import re
import sys
from sentence_transformers import SentenceTransformer
import chromadb
from nltk.tokenize import sent_tokenize
import nltk

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    print("Downloading NLTK punkt_tab data...")
    nltk.download('punkt_tab')

# ---------- Helpers ----------
def clean_text(text: str) -> str:
    text = re.sub(r'\S+@\S+', '', text)   # remove emails
    text = re.sub(r'\d{10,}', '', text)   # remove long numbers
    text = re.sub(r'\s+', ' ', text)      # normalize whitespace
    return text.strip()

def chunk_text(text: str, chunk_size=500, overlap=50):
    sentences = sent_tokenize(text)
    chunks, current, total_words = [], [], 0
    for sentence in sentences:
        words = sentence.split()
        if total_words + len(words) > chunk_size:
            chunks.append(" ".join(current))
            current = current[-overlap:]
            total_words = sum(len(s.split()) for s in current)
        current.append(sentence)
        total_words += len(words)
    if current:
        chunks.append(" ".join(current))
    return chunks

# ---------- Pipeline ----------
def run_pipeline(client_id: str):
    # Get project root directory (2 levels up from current script)
    script_dir = os.path.dirname(os.path.abspath(__file__))  # /path/to/Chatbot/processing
    chatbot_dir = os.path.dirname(script_dir)                # /path/to/Chatbot
    project_root = os.path.dirname(chatbot_dir)              # /path/to/ProjectRoot
    
    # Now construct paths relative to project root
    base_dir = os.path.join(project_root, "backend", "client_data", client_id)
    input_path = os.path.join(base_dir, "website_content.json")
    chunk_path = os.path.join(base_dir, "website_chunks.json")
    embed_path = os.path.join(base_dir, "website_embeddings.json")
    qa_path = os.path.join(base_dir, "custom_qa.json")
    chroma_dir = os.path.join(project_root, "chatbot", "vector-database", "chroma_db")
    
    # Debug info
    print(f"Project root: {project_root}")
    print(f"Looking for input file: {input_path}")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"❌ Crawled data not found for {client_id}: {input_path}")
    
    # 1️⃣ Load crawled website data
    with open(input_path, "r", encoding="utf-8") as f:
        pages = json.load(f)
    
    chunks = []
    for page in pages:
        url, title, content = page.get("url"), page.get("title", ""), page.get("content", "")
        if not content.strip():
            continue
        text = clean_text(content)
        for c in chunk_text(text):
            chunks.append({"url": url, "title": title, "content": c})
    
    # 2️⃣ Add custom Q&A if available
    if os.path.exists(qa_path):
        with open(qa_path, "r", encoding="utf-8") as f:
            qa_pairs = json.load(f)
        for qa in qa_pairs:
            q, a = qa.get("question"), qa.get("answer")
            if q and a:
                chunks.append({
                    "url": "custom_qa",
                    "title": "Q&A",
                    "content": f"Q: {q}\nA: {a}"
                })
        print(f"➕ Added {len(qa_pairs)} custom Q&A entries")
    
    with open(chunk_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(chunks)} chunks to {chunk_path}")
    
    # 3️⃣ Generate embeddings
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode([c["content"] for c in chunks], show_progress_bar=True)
    
    for c, e in zip(chunks, embeddings):
        c["embedding"] = e.tolist()
    
    with open(embed_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved embeddings for {len(chunks)} chunks to {embed_path}")
    
    # 4️⃣ Store in ChromaDB
    try:
        client = chromadb.PersistentClient(path=chroma_dir)
        coll = client.get_or_create_collection(name=client_id.lower())
        ids = [f"{client_id}_chunk_{i}" for i in range(len(chunks))]
        coll.add(
            documents=[c["content"] for c in chunks],
            metadatas=[{"url": c["url"], "title": c["title"]} for c in chunks],
            ids=ids,
            embeddings=[c["embedding"] for c in chunks],
        )
        print(f"🎉 Ingested {len(chunks)} chunks into Chroma collection '{client_id.lower()}'")
    except Exception as e:
        raise RuntimeError(f"❌ Failed to store in ChromaDB: {e}")

# ---------- Entrypoint ----------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python embed_pipeline.py <client_id>")
        sys.exit(1)
    run_pipeline(sys.argv[1])