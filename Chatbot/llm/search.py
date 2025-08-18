from chromadb import PersistentClient

CHROMA_DB_DIR = "vector-database/chroma_db"
COLLECTION_NAME = "website_data"

client = PersistentClient(path=CHROMA_DB_DIR)
collection = client.get_collection(COLLECTION_NAME)

# Get all stored docs
results = collection.get()
for i, doc in enumerate(results["documents"]):
    print(f"--- Document {i+1} ---")
    print(doc[:500])  # print first 500 chars
