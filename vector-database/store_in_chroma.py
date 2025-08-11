# without title


# import chromadb
# import json
# import os
# from typing import List, Dict, Any

# # Path to ChromaDB persistence folder
# CHROMA_DB_DIR = "vector-database/chroma_db"

# # Create a persistent Chroma client
# client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

# # Create or get the collection
# collection = client.get_or_create_collection(name="website_data")

# # Load your website embeddings JSON
# embedding_file = "crawler/crawler/output/website_embeddings.json"  # adjust path if needed

# if not os.path.exists(embedding_file):
#     raise FileNotFoundError(f"❌ Could not find embeddings at: {embedding_file}")

# with open(embedding_file, "r") as f:
#     data = json.load(f)

# print(f"📊 Loaded {len(data)} documents from {embedding_file}")

# # Prepare data
# ids = [str(i) for i in range(len(data))]
# documents = [item["content"] for item in data]
# metadatas = [{"url": item["url"]} for item in data]
# embeddings = [item["embedding"] for item in data]

# # Define batch size (use a safe margin below the limit)
# BATCH_SIZE = 2000

# def batch_data(items: List[Any], batch_size: int) -> List[List[Any]]:
#     """Split a list into batches of specified size."""
#     return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

# # Split all data into batches
# id_batches = batch_data(ids, BATCH_SIZE)
# document_batches = batch_data(documents, BATCH_SIZE)
# metadata_batches = batch_data(metadatas, BATCH_SIZE)
# embedding_batches = batch_data(embeddings, BATCH_SIZE)

# total_batches = len(id_batches)
# print(f"🔄 Processing {total_batches} batches of max {BATCH_SIZE} documents each...")

# # Store each batch
# for i, (id_batch, doc_batch, meta_batch, embed_batch) in enumerate(
#     zip(id_batches, document_batches, metadata_batches, embedding_batches), 1
# ):
#     try:
#         collection.add(
#             documents=doc_batch,
#             metadatas=meta_batch,
#             ids=id_batch,
#             embeddings=embed_batch
#         )
#         print(f"✅ Batch {i}/{total_batches}: Added {len(doc_batch)} documents")
#     except Exception as e:
#         print(f"❌ Error in batch {i}/{total_batches}: {e}")
#         # Optionally, you could try with smaller batches or skip this batch
#         raise

# print(f"🎉 Successfully stored all {len(documents)} documents in ChromaDB at '{CHROMA_DB_DIR}'")

# # Verify the collection
# total_count = collection.count()
# print(f"📈 Collection now contains {total_count} documents")
# 




# 
# with title
# 
# 
import chromadb
import json
import os
from typing import List, Any

# Path to ChromaDB persistence folder
CHROMA_DB_DIR = "vector-database/chroma_db"

# Create a persistent Chroma client
client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

# Create or get the collection
collection = client.get_or_create_collection(name="website_data")

# Load your website embeddings JSON
embedding_file = "crawler/crawler/output/website_embeddings.json"

if not os.path.exists(embedding_file):
    raise FileNotFoundError(f"❌ Could not find embeddings at: {embedding_file}")

with open(embedding_file, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"📊 Loaded {len(data)} documents from {embedding_file}")

# Prepare data
ids = [str(i) for i in range(len(data))]
documents = [item["content"] for item in data]
metadatas = [{"url": item["url"], "title": item.get("title", "")} for item in data]
embeddings = [item["embedding"] for item in data]

# Batch size (keep well below Chroma limits)
BATCH_SIZE = 2000

def batch_data(items: List[Any], batch_size: int) -> List[List[Any]]:
    """Split a list into batches of specified size."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

# Split into batches
id_batches = batch_data(ids, BATCH_SIZE)
document_batches = batch_data(documents, BATCH_SIZE)
metadata_batches = batch_data(metadatas, BATCH_SIZE)
embedding_batches = batch_data(embeddings, BATCH_SIZE)

total_batches = len(id_batches)
print(f"🔄 Processing {total_batches} batches of up to {BATCH_SIZE} documents each...")

# Store each batch
for i, (id_batch, doc_batch, meta_batch, embed_batch) in enumerate(
    zip(id_batches, document_batches, metadata_batches, embedding_batches), 1
):
    try:
        collection.add(
            documents=doc_batch,
            metadatas=meta_batch,
            ids=id_batch,
            embeddings=embed_batch
        )
        print(f"✅ Batch {i}/{total_batches}: Added {len(doc_batch)} documents")
    except Exception as e:
        print(f"❌ Error in batch {i}/{total_batches}: {e}")
        raise

print(f"🎉 Successfully stored all {len(documents)} documents in ChromaDB at '{CHROMA_DB_DIR}'")

# Verify
total_count = collection.count()
print(f"📈 Collection now contains {total_count} documents")
