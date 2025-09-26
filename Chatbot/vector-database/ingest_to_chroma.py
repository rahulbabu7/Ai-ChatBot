# import json
# import os
# from chromadb import PersistentClient
# from sentence_transformers import SentenceTransformer

# # === Configuration ===
# EMBEDDINGS_FILE = "crawler/crawler/output/website_embeddings.json"
# CHROMA_DB_DIR = "vector-database/chroma_db"
# COLLECTION_NAME = "website_data"

# def load_embeddings_to_chromadb():
#     """Load pre-computed embeddings into ChromaDB"""
    
#     # Check if embeddings file exists
#     if not os.path.exists(EMBEDDINGS_FILE):
#         print(f"❌ Embeddings file not found: {EMBEDDINGS_FILE}")
#         print("Please run the embedding script first!")
#         return
    
#     # Load embeddings data
#     print("📂 Loading embeddings...")
#     with open(EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
#         embedded_chunks = json.load(f)
    
#     print(f"Found {len(embedded_chunks)} embedded chunks")
    
#     # Initialize ChromaDB
#     print("🔗 Connecting to ChromaDB...")
#     client = PersistentClient(path=CHROMA_DB_DIR)
    
#     # Delete existing collection if it exists (for fresh start)
#     try:
#         client.delete_collection(COLLECTION_NAME)
#         print(f"🗑️ Deleted existing collection: {COLLECTION_NAME}")
#     except:
#         pass
    
#     # Create new collection
#     collection = client.create_collection(COLLECTION_NAME)
    
#     # Prepare data for ChromaDB
#     documents = []
#     embeddings = []
#     metadatas = []
#     ids = []
    
#     for i, chunk in enumerate(embedded_chunks):
#         documents.append(chunk["content"])
#         embeddings.append(chunk["embedding"])
#         metadatas.append({
#             "source": "crawl",
#             "url": chunk["url"],
#             "title": chunk.get("title", ""),
#             "chunk_id": i
#         })
#         ids.append(f"chunk_{i}")
    
#     # Add to ChromaDB in batches (ChromaDB has limits)
#     batch_size = 100
#     total_batches = len(documents) // batch_size + (1 if len(documents) % batch_size else 0)
    
#     print(f"💾 Adding {len(documents)} documents in {total_batches} batches...")
    
#     for i in range(0, len(documents), batch_size):
#         batch_end = min(i + batch_size, len(documents))
#         batch_num = i // batch_size + 1
        
#         print(f"  Processing batch {batch_num}/{total_batches}")
        
#         collection.add(
#             documents=documents[i:batch_end],
#             embeddings=embeddings[i:batch_end],
#             metadatas=metadatas[i:batch_end],
#             ids=ids[i:batch_end]
#         )
    
#     print("✅ Successfully loaded all embeddings to ChromaDB!")
    
#     # Test the database
#     print("\n🔍 Testing retrieval...")
#     test_results = collection.query(
#         query_texts=["what is this website about"],
#         n_results=3
#     )
    
#     if test_results['documents'] and test_results['documents'][0]:
#         print("✅ Retrieval working! Sample results:")
#         for i, doc in enumerate(test_results['documents'][0][:2]):
#             print(f"  {i+1}. {doc[:100]}...")
#     else:
#         print("❌ No results found in test query")

# if __name__ == "__main__":
#     load_embeddings_to_chromadb()
# 
# 

import os
import json
import fitz  # PyMuPDF
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

# === Config ===
CHROMA_DB_DIR = "vector-database/chroma_db"
COLLECTION_NAME = "website_data"   # unified collection
MODEL_NAME = "all-MiniLM-L6-v2"

# === Init ===
model = SentenceTransformer(MODEL_NAME)
client = PersistentClient(path=CHROMA_DB_DIR)

def get_or_create_collection():
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        return client.create_collection(COLLECTION_NAME)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

# ─────────────────────────────
# Ingest Website Embeddings
# ─────────────────────────────
def ingest_website_embeddings(json_path: str):
    if not os.path.exists(json_path):
        print(f"❌ JSON not found: {json_path}")
        return
    
    with open(json_path, "r", encoding="utf-8") as f:
        embedded_chunks = json.load(f)
    
    print(f"🌍 Found {len(embedded_chunks)} website chunks")
    coll = get_or_create_collection()
    
    documents, embeddings, metadatas, ids = [], [], [], []
    for i, chunk in enumerate(embedded_chunks):
        documents.append(chunk["content"])
        embeddings.append(chunk["embedding"])
        metadatas.append({
            "source": "crawl",
            "url": chunk.get("url", ""),
            "title": chunk.get("title", ""),
            "chunk_id": i
        })
        ids.append(f"crawl_{i}")
    
    coll.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"✅ Ingested {len(documents)} website chunks into {COLLECTION_NAME}")

# ─────────────────────────────
# Ingest PDFs
# ─────────────────────────────
def ingest_pdf(pdf_path: str):
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"📖 Reading {pdf_path}...")
    doc = fitz.open(pdf_path)
    text = "".join([page.get_text("text") + "\n" for page in doc])
    doc.close()
    
    if not text.strip():
        print(f"⚠️ No text extracted from {pdf_path}")
        return
    
    chunks = chunk_text(text)
    embeddings = model.encode(chunks)
    coll = get_or_create_collection()
    
    ids = [f"{os.path.basename(pdf_path)}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": "pdf", "filename": os.path.basename(pdf_path)} for _ in chunks]
    
    coll.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )
    
    print(f"✅ Ingested {len(chunks)} chunks from {pdf_path} into {COLLECTION_NAME}")

# ─────────────────────────────
# Main Runner
# ─────────────────────────────
if __name__ == "__main__":
    # Example usage:
    WEBSITE_JSON = "crawler/crawler/output/website_embeddings.json"
    PDF_DIR = "sample_pdfs"
    
    # 1) Ingest website data
    if os.path.exists(WEBSITE_JSON):
        ingest_website_embeddings(WEBSITE_JSON)
    
    # 2) Ingest all PDFs in folder
    if os.path.exists(PDF_DIR):
        for pdf_file in os.listdir(PDF_DIR):
            if pdf_file.lower().endswith(".pdf"):
                ingest_pdf(os.path.join(PDF_DIR, pdf_file))
    
    print("🎉 Done! Both website + PDF data ingested into Chroma.")
