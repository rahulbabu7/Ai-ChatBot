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
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# === Connect to ChromaDB ===
def connect_to_chromadb():
    try:
        client = PersistentClient(path=CHROMA_DB_DIR)
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        print(f"📊 Connected to ChromaDB. Collection has {count} documents.")
        return collection
    except Exception as e:
        print(f"❌ Error connecting to ChromaDB: {e}")
        return None

collection = connect_to_chromadb()

# === Retrieval Function ===
def retrieve_context(query: str, top_k: int = 4, max_chars: int = 1500) -> str:
    if not collection:
        return ""
    
    try:
        print(f"🔍 Searching for: '{query}'")
        results = collection.query(query_texts=[query], n_results=top_k)
        
        print(f"🔍 Raw results structure: {type(results)}")
        print(f"🔍 Results keys: {results.keys() if results else 'None'}")
        
        docs = results.get('documents', [[]])[0] if results.get('documents') else []
        metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else []
        
        print(f"🔍 Retrieved {len(docs)} documents")
        
        if not docs:
            print("❌ No matching documents found")
            return ""
        
        print(f"✅ Found {len(docs)} relevant chunks")
        
        combined = ""
        for i, doc in enumerate(docs):
            meta = metadatas[i] if i < len(metadatas) else {}
            
            print(f"  📄 Chunk {i+1}: {meta.get('title', 'No title')}")
            print(f"     Content length: {len(doc)} chars")
            print(f"     Preview: {doc[:150]}...")
            
            # Add document content with clear separation
            if doc and doc.strip():  # Make sure doc is not empty
                if len(combined) + len(doc) > max_chars:
                    # Add partial content if we're near the limit
                    remaining_chars = max_chars - len(combined)
                    if remaining_chars > 100:  # Only add if meaningful amount remains
                        combined += doc[:remaining_chars].strip() + "\n\n"
                    break
                combined += doc.strip() + "\n\n"
            else:
                print(f"     ⚠️ Empty or whitespace-only document at index {i}")
        
        print(f"\n📝 COMBINED CONTEXT ({len(combined)} chars):")
        print("-" * 60)
        if combined:
            print(combined[:500] + ("..." if len(combined) > 500 else ""))
        else:
            print("❌ EMPTY CONTEXT - No valid content found!")
        print("-" * 60)
        
        return combined.strip()
        
    except Exception as e:
        print(f"❌ Error during retrieval: {e}")
        import traceback
        traceback.print_exc()
        return ""

# === Simple Chat Function (Debug Version) ===
def debug_chat_with_model(query: str) -> str:
    if not collection:
        return "❌ Database not available."
    
    print("\n" + "="*50)
    context = retrieve_context(query)

    if not context:
        return "I couldn't find relevant information in the database for your query."

    # Simple prompt format for debugging
    prompt = f"""Context from website:
{context}

Question: {query}
Answer: Based on the context above,"""

    print(f"\n🔤 FULL PROMPT:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)

    try:
        # Tokenize with simpler approach
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1500,
            padding=True
        ).to(model.device)
        
        print(f"📊 Input tokens: {inputs['input_ids'].shape[1]}")
        print("🤖 Generating response...")
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                do_sample=True,
                temperature=0.3,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        # Decode only the new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = tokenizer.decode(new_tokens, skip_special_tokens=True)
        
        print(f"\n🔤 RAW RESPONSE:")
        print("-" * 40)
        print(f"'{response}'")
        print("-" * 40)
        
        return response.strip()
        
    except Exception as e:
        print(f"❌ Generation error: {e}")
        return f"Error generating response: {e}"

# === Alternative: Just show context without model ===
def context_only_test(query: str):
    print("\n" + "="*60)
    print("🧪 CONTEXT-ONLY TEST (No Model Generation)")
    print("="*60)
    
    context = retrieve_context(query)
    if context:
        print(f"\n✅ Retrieved context for '{query}':")
        print("\n" + "="*40)
        print(context)
        print("="*40)
        print(f"\nBased on this context, the college name appears to be in the content above.")
        
        # Try to extract college name manually
        if "SJCET" in context:
            print("\n🎯 DETECTED: College name appears to be 'SJCET' (found in context)")
        if "St. Joseph" in context or "Saint Joseph" in context:
            print("🎯 DETECTED: Full name likely contains 'St. Joseph'")
    else:
        print("❌ No context retrieved")

# === CLI ===
if __name__ == "__main__":
    if not collection:
        exit(1)
    
    print("\n💬 Debug Chat - Testing RAG System")
    print("Commands:")
    print("  - Type a question normally for full RAG")
    print("  - Type 'context: [question]' to see just retrieved context")
    print("  - Type 'exit' to quit")
    print("="*60)
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
            
        try:
            if user_input.startswith("context:"):
                query = user_input[8:].strip()
                context_only_test(query)
            else:
                response = debug_chat_with_model(user_input)
                print(f"\n🤖 Assistant: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")