## without title


# from sentence_transformers import SentenceTransformer
# import chromadb

# # Path to ChromaDB persistence folder
# CHROMA_DB_DIR = "vector-database/chroma_db"

# # Create a persistent Chroma client (modern syntax)
# client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

# # Get the collection (make sure this matches the name used in storage)
# try:
#     collection = client.get_collection("website_data")  # Changed from "website_docs" to match storage script
#     print(f"📊 Collection found with {collection.count()} documents")
# except Exception as e:
#     print(f"❌ Error getting collection: {e}")
#     print("Available collections:")
#     collections = client.list_collections()
#     for col in collections:
#         print(f"  - {col.name}")
#     exit(1)

# # Load embedder (same model used for creating embeddings)
# print("🔄 Loading sentence transformer model...")
# model = SentenceTransformer("all-MiniLM-L6-v2")

# def search_documents(query: str, n_results: int = 5):
#     """Search for documents similar to the query."""
#     print(f"🔍 Searching for: '{query}'")
    
#     # Generate query embedding
#     query_vector = model.encode(query).tolist()
    
#     # Search the collection
#     try:
#         results = collection.query(
#             query_embeddings=[query_vector],
#             n_results=n_results
#         )
        
#         # Display results
#         if not results["documents"][0]:
#             print("❌ No results found!")
#             return
            
#         print(f"\n🎯 Found {len(results['documents'][0])} results:")
#         print("=" * 80)
        
#         for i in range(len(results["documents"][0])):
#             print(f"\n--- Result #{i+1} ---")
#             print(f"🌐 URL: {results['metadatas'][0][i]['url']}")
#             print(f"📏 Distance: {results['distances'][0][i]:.4f}")
            
#             # Show content preview (first 500 chars)
#             content = results['documents'][0][i]
#             if len(content) > 500:
#                 print(f"📝 Content: {content[:500]}...")
#             else:
#                 print(f"📝 Content: {content}")
            
#             print("-" * 80)
            
#     except Exception as e:
#         print(f"❌ Error during search: {e}")

# # Interactive query loop
# def main():
#     print("🚀 ChromaDB Query Interface Ready!")
#     print("Type 'quit' or 'exit' to stop")
    
#     while True:
#         try:
#             query = input("\n🔍 Ask your question: ").strip()
            
#             if query.lower() in ['quit', 'exit', 'q']:
#                 print("👋 Goodbye!")
#                 break
                
#             if not query:
#                 print("❌ Please enter a question!")
#                 continue
                
#             search_documents(query)
            
#         except KeyboardInterrupt:
#             print("\n👋 Goodbye!")
#             break
#         except Exception as e:
#             print(f"❌ Error: {e}")

# if __name__ == "__main__":
#     main()
# 
# 
# 


#with title
# 
# 

from sentence_transformers import SentenceTransformer
import chromadb

# Path to ChromaDB persistence folder
CHROMA_DB_DIR = "vector-database/chroma_db"

# Create a persistent Chroma client
client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

# Get the collection
try:
    collection = client.get_collection("website_data")
    print(f"📊 Collection found with {collection.count()} documents")
except Exception as e:
    print(f"❌ Error getting collection: {e}")
    print("Available collections:")
    for col in client.list_collections():
        print(f"  - {col.name}")
    exit(1)

# Load embedder (must match embedding creation)
print("🔄 Loading sentence transformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

def search_documents(query: str, n_results: int = 5):
    """Search for documents similar to the query."""
    print(f"🔍 Searching for: '{query}'")
    
    # Generate query embedding
    query_vector = model.encode(query).tolist()
    
    try:
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=n_results
        )
        
        if not results["documents"][0]:
            print("❌ No results found!")
            return
            
        print(f"\n🎯 Found {len(results['documents'][0])} results:")
        print("=" * 80)
        
        for i in range(len(results["documents"][0])):
            metadata = results['metadatas'][0][i]
            url = metadata.get("url", "N/A")
            title = metadata.get("title", "").strip() or "(No title)"
            distance = results['distances'][0][i]
            content = results['documents'][0][i]
            
            print(f"\n--- Result #{i+1} ---")
            print(f"🏷  Title: {title}")
            print(f"🌐 URL: {url}")
            print(f"📏 Distance: {distance:.4f}")
            print(f"📝 Content preview: {content[:500]}{'...' if len(content) > 500 else ''}")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Error during search: {e}")

def main():
    print("🚀 ChromaDB Query Interface Ready!")
    print("Type 'quit' or 'exit' to stop")
    
    while True:
        try:
            query = input("\n🔍 Ask your question: ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            if not query:
                print("❌ Please enter a question!")
                continue
            search_documents(query)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
