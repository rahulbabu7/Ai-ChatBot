# from transformers import AutoTokenizer, AutoModelForCausalLM
# from chromadb import PersistentClient
# import torch

# MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# # ✅ Force CPU or smaller precision to avoid OOM
# model = AutoModelForCausalLM.from_pretrained(
#     MODEL_ID,
#     torch_dtype=torch.float16,
#     device_map="auto",
#     low_cpu_mem_usage=True
# )
# tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

# CHROMA_DB_DIR = "vector-database/chroma_db"
# client = PersistentClient(path=CHROMA_DB_DIR)
# collection = client.get_or_create_collection("website_data")

# def retrieve_context(query: str, top_k: int = 4, max_chars: int = 1500):
#     """Get top matching chunks but limit size to fit model context."""
#     results = collection.query(query_texts=[query], n_results=top_k)
#     docs = results['documents'][0]
#     combined = ""
#     for doc in docs:
#         if len(combined) + len(doc) > max_chars:
#             break
#         combined += doc.strip() + "\n"
#     return combined

# def build_prompt(context: str, user_input: str):
#     return [
#         {"role": "system", "content": "You are a helpful assistant. Use the following website content to answer questions:\n" + context},
#         {"role": "user", "content": user_input}
#     ]

# def chat_with_model(query: str):
#     context = retrieve_context(query)

#     messages = build_prompt(context, query)

#     inputs = tokenizer.apply_chat_template(
#         messages,
#         add_generation_prompt=True,
#         tokenize=True,
#         return_dict=True,
#         return_tensors="pt",
#         truncation=True,            # ✅ Prevents token overflow
#         max_length=2048             # ✅ Fits model's context size
#     ).to(model.device)

#     outputs = model.generate(
#         **inputs,
#         max_new_tokens=300,
#         do_sample=True,
#         temperature=0.7,
#         top_p=0.95
#     )

#     response = tokenizer.decode(
#         outputs[0][inputs["input_ids"].shape[-1]:],
#         skip_special_tokens=True
#     )
#     return response.strip()

# if __name__ == "__main__":
#     print("💬 Ask me anything (type 'exit' to quit)")
#     while True:
#         user_input = input("You: ")
#         if user_input.lower() in ['exit', 'quit']:
#             break
#         try:
#             print("🤖", chat_with_model(user_input))
#         except Exception as e:
#             print("❌ Error:", e)




from transformers import AutoTokenizer, AutoModelForCausalLM
from chromadb import PersistentClient
import torch
import os

# === Model Config ===
MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
CHROMA_DB_DIR = "vector-database/chroma_db"
COLLECTION_NAME = "website_data"

# === Load Model & Tokenizer ===
print("🚀 Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
    low_cpu_mem_usage=True
)
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

# === Connect to ChromaDB ===
def connect_to_chromadb():
    """Connect to ChromaDB with error handling"""
    try:
        if not os.path.exists(CHROMA_DB_DIR):
            print(f"❌ ChromaDB directory not found: {CHROMA_DB_DIR}")
            print("Please run load_embeddings_to_chromadb.py first!")
            return None
        
        client = PersistentClient(path=CHROMA_DB_DIR)
        collection = client.get_collection(COLLECTION_NAME)
        
        # Test if collection has data
        count = collection.count()
        print(f"📊 Connected to ChromaDB. Collection has {count} documents.")
        
        if count == 0:
            print("⚠️ Collection is empty! Please load your embeddings first.")
            return None
            
        return collection
        
    except Exception as e:
        print(f"❌ Error connecting to ChromaDB: {e}")
        print("Make sure you've run load_embeddings_to_chromadb.py first!")
        return None

collection = connect_to_chromadb()

# === Retrieval Function ===
def retrieve_context(query: str, top_k: int = 4, max_chars: int = 1500) -> str:
    """Retrieve top matching chunks from ChromaDB and combine into context."""
    if not collection:
        return ""
    
    try:
        print(f"🔍 Searching for: '{query}'")
        results = collection.query(query_texts=[query], n_results=top_k)
        
        docs = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        
        if not docs:
            print("❌ No matching documents found")
            return ""
        
        print(f"✅ Found {len(docs)} relevant chunks")
        
        combined = ""
        for i, (doc, meta) in enumerate(zip(docs, metadatas)):
            print(f"  📄 Chunk {i+1}: {meta.get('title', 'No title')} ({meta.get('url', 'No URL')})")
            print(f"     Preview: {doc[:100]}...")
            
            if len(combined) + len(doc) > max_chars:
                break
            combined += doc.strip() + "\n\n"
        
        return combined.strip()
        
    except Exception as e:
        print(f"❌ Error during retrieval: {e}")
        return ""

# === Prompt Builder ===
def build_prompt(context: str, user_input: str):
    """Create a chat-style prompt for TinyLlama."""
    return [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. Use the following extracted content "
                "from a website to answer the user's question accurately. "
                "If the information is not in the provided context, say so clearly.\n\n"
                f"Context:\n{context}"
            )
        },
        {"role": "user", "content": user_input}
    ]

# === Main Chat Function ===
def chat_with_model(query: str) -> str:
    """Retrieve context, build prompt, and get model response."""
    if not collection:
        return "❌ Database not available. Please run load_embeddings_to_chromadb.py first!"
    
    print("\n" + "="*50)
    context = retrieve_context(query)

    if not context:
        return "I couldn't find relevant information in the database for your query."

    print(f"\n🧠 Retrieved context ({len(context)} chars)")
    print("="*50)
    
    messages = build_prompt(context, query)

    try:
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        ).to(model.device)

        print("🤖 Generating response...")
        
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            pad_token_id=tokenizer.eos_token_id
        )

        response = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True
        )
        return response.strip()
        
    except Exception as e:
        return f"❌ Error generating response: {e}"

# === CLI ===
if __name__ == "__main__":
    if not collection:
        print("\n💡 To fix this issue:")
        print("1. Make sure you've scraped a website")
        print("2. Run the embedding script")
        print("3. Run: python load_embeddings_to_chromadb.py")
        exit(1)
    
    print("\n💬 Ask me anything about the scraped website (type 'exit' to quit)")
    print("="*60)
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
            
        try:
            response = chat_with_model(user_input)
            print(f"\n🤖 Assistant: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")