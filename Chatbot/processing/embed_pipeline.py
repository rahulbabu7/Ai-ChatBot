# import os
# import json
# import re
# import sys
# from sentence_transformers import SentenceTransformer
# import chromadb
# from nltk.tokenize import sent_tokenize
# import nltk

# # Download required NLTK data
# try:
#     nltk.data.find('tokenizers/punkt_tab')
# except LookupError:
#     print("Downloading NLTK punkt_tab data...")
#     nltk.download('punkt_tab')

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

# def batch_add_to_chroma(collection, chunks, client_id, max_batch_size=5000):
#     """Add chunks to ChromaDB in batches to avoid size limits"""
#     total_chunks = len(chunks)
#     print(f"📦 Adding {total_chunks} chunks in batches of {max_batch_size}")
    
#     for i in range(0, total_chunks, max_batch_size):
#         batch_end = min(i + max_batch_size, total_chunks)
#         batch_chunks = chunks[i:batch_end]
        
#         batch_ids = [f"{client_id}_chunk_{j}" for j in range(i, batch_end)]
#         batch_documents = [c["content"] for c in batch_chunks]
#         batch_metadatas = [{"url": c["url"], "title": c["title"]} for c in batch_chunks]
#         batch_embeddings = [c["embedding"] for c in batch_chunks]
        
#         print(f"  📋 Processing batch {i//max_batch_size + 1}: chunks {i+1}-{batch_end}")
        
#         try:
#             collection.add(
#                 documents=batch_documents,
#                 metadatas=batch_metadatas,
#                 ids=batch_ids,
#                 embeddings=batch_embeddings,
#             )
#             print(f"  ✅ Successfully added batch {i//max_batch_size + 1}")
#         except Exception as e:
#             print(f"  ❌ Failed to add batch {i//max_batch_size + 1}: {e}")
#             raise

# # ---------- Pipeline ----------
# def run_pipeline(client_id: str):
#     # Get project root directory (2 levels up from current script)
#     script_dir = os.path.dirname(os.path.abspath(__file__))  # /path/to/Chatbot/processing
#     chatbot_dir = os.path.dirname(script_dir)                # /path/to/Chatbot
#     project_root = os.path.dirname(chatbot_dir)              # /path/to/ProjectRoot
    
#     # Now construct paths relative to project root
#     base_dir = os.path.join(project_root, "backend", "client_data", client_id)
#     input_path = os.path.join(base_dir, "website_content.json")
#     chunk_path = os.path.join(base_dir, "website_chunks.json")
#     embed_path = os.path.join(base_dir, "website_embeddings.json")
#     qa_path = os.path.join(base_dir, "custom_qa.json")
#     chroma_dir = os.path.join(project_root, "chatbot", "vector-database", "chroma_db")
    
#     # Debug info
#     print(f"Project root: {project_root}")
#     print(f"Looking for input file: {input_path}")
    
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
    
#     # 4️⃣ Store in ChromaDB with batching
#     try:
#         client = chromadb.PersistentClient(path=chroma_dir)
        
#         # Delete existing collection if it exists to avoid duplicates
#         try:
#             client.delete_collection(name=client_id.lower())
#             print(f"🗑️  Deleted existing collection '{client_id.lower()}'")
#         except:
#             pass  # Collection doesn't exist, which is fine
            
#         coll = client.get_or_create_collection(name=client_id.lower())
        
#         # Add chunks in batches
#         batch_add_to_chroma(coll, chunks, client_id)
        
#         print(f"🎉 Successfully ingested {len(chunks)} chunks into Chroma collection '{client_id.lower()}'")
        
#         # Verify the ingestion
#         collection_count = coll.count()
#         print(f"🔍 Verification: Collection now contains {collection_count} documents")
        
#     except Exception as e:
#         raise RuntimeError(f"❌ Failed to store in ChromaDB: {e}")

# # ---------- Entrypoint ----------
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python embed_pipeline.py <client_id>")
#         sys.exit(1)
#     run_pipeline(sys.argv[1])
# 

import os
import sys
import json
import re
from sentence_transformers import SentenceTransformer
import chromadb
from nltk.tokenize import sent_tokenize
import nltk

# -------------------------
# Download NLTK punkt if missing
# -------------------------
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# -------------------------
# Helper functions
# -------------------------
def clean_text(text: str) -> str:
    """Remove emails, long numbers, and normalize whitespace."""
    text = re.sub(r'\S+@\S+', '', text)      # remove emails
    text = re.sub(r'\d{10,}', '', text)      # remove long numbers
    text = re.sub(r'\s+', ' ', text)         # normalize spaces
    return text.strip()

def chunk_text(text: str, chunk_size=500, overlap=50):
    """Chunk text into overlapping chunks."""
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

def batch_add_to_chroma(collection, chunks, client_id, max_batch_size=5000):
    """Add chunks to ChromaDB in batches to avoid size limits."""
    total_chunks = len(chunks)
    print(f"📦 Adding {total_chunks} chunks in batches of {max_batch_size}")

    for i in range(0, total_chunks, max_batch_size):
        batch_end = min(i + max_batch_size, total_chunks)
        batch_chunks = chunks[i:batch_end]

        batch_ids = [f"{client_id}_chunk_{j}" for j in range(i, batch_end)]
        batch_documents = [c["content"] for c in batch_chunks]
        batch_metadatas = []
        
        # Create metadata based on source type
        for c in batch_chunks:
            metadata = {
                "source": c.get("source", "unknown"),
                "title": c.get("title", "")
            }
            
            if c.get("source") == "crawl":
                metadata["url"] = c.get("url", "")
            elif c.get("source") == "pdf":
                metadata["filename"] = c.get("filename", "")
            elif c.get("source") == "qa":
                metadata["type"] = "custom_qa"
            
            batch_metadatas.append(metadata)
        
        batch_embeddings = [c["embedding"] for c in batch_chunks]

        print(f"  📋 Processing batch {i//max_batch_size + 1}: chunks {i+1}-{batch_end}")
        try:
            collection.add(
                documents=batch_documents,
                metadatas=batch_metadatas,
                ids=batch_ids,
                embeddings=batch_embeddings,
            )
            print(f"  ✅ Successfully added batch {i//max_batch_size + 1}")
        except Exception as e:
            print(f"  ❌ Failed to add batch {i//max_batch_size + 1}: {e}")
            raise

# -------------------------
# Main pipeline
# -------------------------
def run_pipeline(client_id: str, source_type="crawl"):
    """
    source_type: "crawl" or "pdf"
    """
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))  # /Chatbot/processing
    chatbot_dir = os.path.dirname(script_dir)                # /Chatbot
    project_root = os.path.dirname(chatbot_dir)              # /ProjectRoot
    base_dir = os.path.join(project_root, "backend", "client_data", client_id)
    chroma_dir = os.path.join(project_root, "chatbot", "vector-database", "chroma_db")

    # Output files
    chunk_path = os.path.join(base_dir, "chunks.json")
    embed_path = os.path.join(base_dir, "embeddings.json")
    qa_path = os.path.join(base_dir, "custom_qa.json")

    chunks = []

    # -------------------------
    # Load data based on source type
    # -------------------------
    if source_type == "pdf":
        input_path = os.path.join(base_dir, "custom_pdf.txt")
        pdf_path = os.path.join(base_dir, "custom_pdf.pdf")
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"❌ PDF text not found for {client_id}")
        
        # Get original PDF filename if available
        pdf_filename = "custom_pdf.pdf"
        if os.path.exists(pdf_path):
            pdf_filename = os.path.basename(pdf_path)
            
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        for c in chunk_text(clean_text(text)):
            chunks.append({
                "source": "pdf",
                "filename": pdf_filename,
                "title": f"PDF: {pdf_filename}",
                "content": c
            })
        print(f"📄 Loaded PDF and created {len(chunks)} chunks")
        
    else:  # crawl
        input_path = os.path.join(base_dir, "website_content.json")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"❌ Crawled data not found for {client_id}")
            
        with open(input_path, "r", encoding="utf-8") as f:
            pages = json.load(f)
            
        for page in pages:
            url, title, content = page.get("url"), page.get("title", ""), page.get("content", "")
            if not content.strip():
                continue
            text = clean_text(content)
            for c in chunk_text(text):
                chunks.append({
                    "source": "crawl",
                    "url": url,
                    "title": title,
                    "content": c
                })
        print(f"🌐 Loaded website crawl and created {len(chunks)} chunks")

    # -------------------------
    # Add custom Q&A (works with both sources)
    # -------------------------
    if os.path.exists(qa_path):
        with open(qa_path, "r", encoding="utf-8") as f:
            qa_pairs = json.load(f)
        for qa in qa_pairs:
            q, a = qa.get("question"), qa.get("answer")
            if q and a:
                chunks.append({
                    "source": "qa",
                    "title": "Q&A",
                    "content": f"Q: {q}\nA: {a}"
                })
        print(f"➕ Added {len(qa_pairs)} custom Q&A entries")

    # Save chunks
    with open(chunk_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(chunks)} chunks to {chunk_path}")

    # -------------------------
    # Generate embeddings
    # -------------------------
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode([c["content"] for c in chunks], show_progress_bar=True)
    for c, e in zip(chunks, embeddings):
        c["embedding"] = e.tolist()

    with open(embed_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved embeddings for {len(chunks)} chunks to {embed_path}")

    # -------------------------
    # Store in ChromaDB
    # -------------------------
    try:
        client = chromadb.PersistentClient(path=chroma_dir)

        # Delete existing collection if exists
        try:
            client.delete_collection(name=client_id.lower())
            print(f"🗑️  Deleted existing collection '{client_id.lower()}'")
        except:
            pass

        coll = client.get_or_create_collection(name=client_id.lower())

        batch_add_to_chroma(coll, chunks, client_id)

        print(f"🎉 Successfully ingested {len(chunks)} chunks into Chroma collection '{client_id.lower()}'")
        print(f"🔍 Collection now contains {coll.count()} documents")

    except Exception as e:
        raise RuntimeError(f"❌ Failed to store in ChromaDB: {e}")

# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python embed_pipeline.py <client_id> [source_type]")
        sys.exit(1)
    client_id = sys.argv[1]
    source_type = sys.argv[2] if len(sys.argv) > 2 else "crawl"
    run_pipeline(client_id, source_type)
