import json
import os
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

# === Configuration ===
EMBEDDINGS_FILE = "crawler/crawler/output/website_embeddings.json"
CHROMA_DB_DIR = "vector-database/chroma_db"
COLLECTION_NAME = "website_data"

def load_embeddings_to_chromadb():
    """Load pre-computed embeddings into ChromaDB"""
    
    # Check if embeddings file exists
    if not os.path.exists(EMBEDDINGS_FILE):
        print(f"❌ Embeddings file not found: {EMBEDDINGS_FILE}")
        print("Please run the embedding script first!")
        return
    
    # Load embeddings data
    print("📂 Loading embeddings...")
    with open(EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
        embedded_chunks = json.load(f)
    
    print(f"Found {len(embedded_chunks)} embedded chunks")
    
    # Initialize ChromaDB
    print("🔗 Connecting to ChromaDB...")
    client = PersistentClient(path=CHROMA_DB_DIR)
    
    # Delete existing collection if it exists (for fresh start)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"🗑️ Deleted existing collection: {COLLECTION_NAME}")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(COLLECTION_NAME)
    
    # Prepare data for ChromaDB
    documents = []
    embeddings = []
    metadatas = []
    ids = []
    
    for i, chunk in enumerate(embedded_chunks):
        documents.append(chunk["content"])
        embeddings.append(chunk["embedding"])
        metadatas.append({
            "url": chunk["url"],
            "title": chunk.get("title", ""),
            "chunk_id": i
        })
        ids.append(f"chunk_{i}")
    
    # Add to ChromaDB in batches (ChromaDB has limits)
    batch_size = 100
    total_batches = len(documents) // batch_size + (1 if len(documents) % batch_size else 0)
    
    print(f"💾 Adding {len(documents)} documents in {total_batches} batches...")
    
    for i in range(0, len(documents), batch_size):
        batch_end = min(i + batch_size, len(documents))
        batch_num = i // batch_size + 1
        
        print(f"  Processing batch {batch_num}/{total_batches}")
        
        collection.add(
            documents=documents[i:batch_end],
            embeddings=embeddings[i:batch_end],
            metadatas=metadatas[i:batch_end],
            ids=ids[i:batch_end]
        )
    
    print("✅ Successfully loaded all embeddings to ChromaDB!")
    
    # Test the database
    print("\n🔍 Testing retrieval...")
    test_results = collection.query(
        query_texts=["what is this website about"],
        n_results=3
    )
    
    if test_results['documents'] and test_results['documents'][0]:
        print("✅ Retrieval working! Sample results:")
        for i, doc in enumerate(test_results['documents'][0][:2]):
            print(f"  {i+1}. {doc[:100]}...")
    else:
        print("❌ No results found in test query")

if __name__ == "__main__":
    load_embeddings_to_chromadb()