# from transformers import AutoTokenizer, AutoModelForCausalLM
# from chromadb import PersistentClient
# import torch
# import os
# import json
# from sentence_transformers import SentenceTransformer, util

# # === Model Config ===
# MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
# CHROMA_DB_DIR = "vector-database/chroma_db"
# COLLECTION_NAME = "website_data"

# # === Load Model & Tokenizer ===
# print("🚀 Loading model...")
# model = AutoModelForCausalLM.from_pretrained(
#     MODEL_ID,
#     torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
#     device_map="auto",
#     low_cpu_mem_usage=True
# )
# tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
# if tokenizer.pad_token is None:
#     tokenizer.pad_token = tokenizer.eos_token

# # === Load SentenceTransformer for Q&A Matching ===
# qa_model = SentenceTransformer("all-MiniLM-L6-v2")

# def load_custom_qa(path="llm/custom_qa.json"):
#     with open(path, "r", encoding="utf-8") as f:
#         qa_pairs = json.load(f)
#     for qa in qa_pairs:
#         qa["embedding"] = qa_model.encode(qa["question"])
#     return qa_pairs

# custom_qa = load_custom_qa()

# def find_custom_answer(query, threshold=0.8):
#     query_emb = qa_model.encode(query)
#     best_score = 0
#     best_answer = None
#     for qa in custom_qa:
#         score = util.cos_sim(query_emb, qa["embedding"]).item()
#         if score > best_score:
#             best_score = score
#             best_answer = qa["answer"]
#     if best_score >= threshold:
#         return best_answer
#     return None

# # === Connect to ChromaDB ===
# def connect_to_chromadb():
#     try:
#         if not os.path.exists(CHROMA_DB_DIR):
#             print(f"❌ ChromaDB directory not found: {CHROMA_DB_DIR}")
#             return None
        
#         client = PersistentClient(path=CHROMA_DB_DIR)
#         collection = client.get_collection(COLLECTION_NAME)
#         count = collection.count()
#         print(f"📊 Connected to ChromaDB. Collection has {count} documents.")
        
#         if count == 0:
#             print("⚠️ Collection is empty!")
#             return None
#         return collection
#     except Exception as e:
#         print(f"❌ Error connecting to ChromaDB: {e}")
#         return None

# collection = connect_to_chromadb()

# # === Retrieve Context from Chroma ===
# def retrieve_context(query: str, top_k: int = 4, max_chars: int = 1500) -> str:
#     if not collection:
#         return ""
#     try:
#         results = collection.query(query_texts=[query], n_results=top_k)
#         docs = results.get('documents', [[]])[0]
#         if not docs:
#             return ""
#         combined = ""
#         for doc in docs:
#             if len(combined) + len(doc) > max_chars:
#                 break
#             combined += doc.strip() + "\n\n"
#         return combined.strip()
#     except Exception:
#         return ""

# # === Prompt Builder ===
# def build_prompt(context: str, user_input: str):
#     return f"""Context from SJCET Palai website:
# {context}

# Question: {user_input}

# Answer: Based on the information provided above,"""

# # === Main Chat Function ===
# def chat_with_model(query: str) -> str:
#     # 1️⃣ Check custom Q&A first
#     custom_answer = find_custom_answer(query)
#     if custom_answer:
#         return custom_answer
    
#     # 2️⃣ Otherwise, retrieve from Chroma + LLM
#     context = retrieve_context(query)
#     if not context:
#         return "I couldn't find relevant information in the database for your query."

#     prompt = build_prompt(context, query)
#     inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1800, padding=True).to(model.device)
    
#     with torch.no_grad():
#         outputs = model.generate(
#             **inputs,
#             max_new_tokens=150,
#             do_sample=True,
#             temperature=0.3,
#             top_p=0.9,
#             pad_token_id=tokenizer.eos_token_id
#         )

#     new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
#     return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

# # === CLI ===
# if __name__ == "__main__":
#     if not collection:
#         exit(1)
#     print("\n💬 Ask me anything (type 'exit' to quit)")
#     while True:
#         user_input = input("\nYou: ").strip()
#         if user_input.lower() in {"exit", "quit"}:
#             break
#         print(f"\n🤖 Assistant: {chat_with_model(user_input)}")






# from transformers import AutoTokenizer, AutoModelForCausalLM
# from chromadb import PersistentClient
# import torch
# import os
# import json
# from sentence_transformers import SentenceTransformer, util

# # === Model Config ===
# MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
# CHROMA_DB_DIR = "vector-database/chroma_db"
# COLLECTION_NAME = "website_data"

# # === Load Model & Tokenizer ===
# print("🚀 Loading model...")
# model = AutoModelForCausalLM.from_pretrained(
#     MODEL_ID,
#     torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
#     device_map="auto",
#     low_cpu_mem_usage=True
# )
# tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
# if tokenizer.pad_token is None:
#     tokenizer.pad_token = tokenizer.eos_token

# # === Load SentenceTransformer for Q&A Matching ===
# print("🔧 Loading similarity model...")
# qa_model = SentenceTransformer("all-MiniLM-L6-v2")

# # === Built-in Custom Q&A (No external file needed) ===
# CUSTOM_QA = [
#     {
#         "questions": [
#             "what is the name of the principal",
#             "who is the principal",
#             "principal name",
#             "who is the principal of sjcet",
#             "name of principal",
#             "principal of the college"
#         ],
#         "answer": "The principal of SJCET Palai is Dr. V.P. Devassia."
#     },
#     {
#         "questions": [
#             "what is the name of the college",
#             "college name",
#             "name of college",
#             "what college is this",
#             "which college"
#         ],
#         "answer": "The college name is SJCET (St. Joseph's College of Engineering and Technology), Palai."
#     },
#     {
#         "questions": [
#             "where is the college located",
#             "college location",
#             "address of college",
#             "where is sjcet"
#         ],
#         "answer": "SJCET is located in Palai, Kerala, India."
#     },
#     {
#         "questions": [
#             "what is sjcet",
#             "about sjcet",
#             "tell me about the college",
#             "college information"
#         ],
#         "answer": "SJCET (St. Joseph's College of Engineering and Technology) is an engineering college located in Palai, Kerala. The principal is Dr. V.P. Devassia."
#     }
# ]

# # Pre-compute embeddings for all questions
# print("🧮 Computing question embeddings...")
# for qa in CUSTOM_QA:
#     qa["embeddings"] = [qa_model.encode(q) for q in qa["questions"]]

# def find_custom_answer(query, threshold=0.7):
#     """Find custom answer using semantic similarity"""
#     query_emb = qa_model.encode(query)
#     best_score = 0
#     best_answer = None
    
#     for qa in CUSTOM_QA:
#         for question_emb in qa["embeddings"]:
#             score = util.cos_sim(query_emb, question_emb).item()
#             if score > best_score:
#                 best_score = score
#                 best_answer = qa["answer"]
    
#     if best_score >= threshold:
#         print(f"✅ Found custom answer (similarity: {best_score:.2f})")
#         return best_answer
#     return None

# # === Connect to ChromaDB ===
# def connect_to_chromadb():
#     """Connect to ChromaDB with better error handling"""
#     try:
#         if not os.path.exists(CHROMA_DB_DIR):
#             print(f"⚠️ ChromaDB directory not found: {CHROMA_DB_DIR}")
#             print("RAG fallback will be disabled, but custom Q&A will still work.")
#             return None
        
#         client = PersistentClient(path=CHROMA_DB_DIR)
#         collection = client.get_collection(COLLECTION_NAME)
#         count = collection.count()
#         print(f"📊 Connected to ChromaDB. Collection has {count} documents.")
        
#         if count == 0:
#             print("⚠️ Collection is empty! Only custom Q&A will work.")
#             return None
#         return collection
        
#     except Exception as e:
#         print(f"⚠️ ChromaDB error: {e}")
#         print("Continuing with custom Q&A only.")
#         return None

# collection = connect_to_chromadb()

# # === Improved Retrieval Function ===
# def retrieve_context(query: str, top_k: int = 4, max_chars: int = 1500) -> str:
#     """Retrieve context from ChromaDB with better handling"""
#     if not collection:
#         return ""
    
#     try:
#         results = collection.query(query_texts=[query], n_results=top_k)
#         docs = results.get('documents', [[]])[0] if results.get('documents') else []
        
#         if not docs:
#             return ""
        
#         print(f"🔍 Retrieved {len(docs)} relevant chunks from database")
        
#         combined = ""
#         for doc in docs:
#             if doc and doc.strip():  # Ensure doc is not empty
#                 if len(combined) + len(doc) > max_chars:
#                     # Add partial content if near limit
#                     remaining = max_chars - len(combined)
#                     if remaining > 100:
#                         combined += doc[:remaining].strip() + "\n\n"
#                     break
#                 combined += doc.strip() + "\n\n"
        
#         return combined.strip()
        
#     except Exception as e:
#         print(f"❌ Retrieval error: {e}")
#         return ""

# # === Better Prompt Builder ===
# def build_prompt(context: str, user_input: str):
#     """Create optimized prompt for TinyLlama"""
#     return f"""Based on the following information about SJCET Palai:

# {context}

# Question: {user_input}
# Answer:"""

# # === Enhanced Response Generation ===
# def generate_llm_response(prompt: str) -> str:
#     """Generate response from LLM with better parameters"""
#     try:
#         inputs = tokenizer(
#             prompt, 
#             return_tensors="pt", 
#             truncation=True, 
#             max_length=1600,  # Leave room for response
#             padding=True
#         ).to(model.device)
        
#         with torch.no_grad():
#             outputs = model.generate(
#                 **inputs,
#                 max_new_tokens=200,
#                 do_sample=True,
#                 temperature=0.4,  # Slightly higher for more natural responses
#                 top_p=0.9,
#                 pad_token_id=tokenizer.eos_token_id,
#                 eos_token_id=tokenizer.eos_token_id,
#                 repetition_penalty=1.1  # Reduce repetition
#             )

#         # Decode only new tokens
#         new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
#         response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        
#         # Clean up response
#         if response and len(response) > 5:
#             # Remove incomplete sentences at the end
#             sentences = response.split('.')
#             if len(sentences) > 1 and len(sentences[-1].strip()) < 10:
#                 response = '.'.join(sentences[:-1]) + '.'
            
#             return response
        
#         return "I found some information but couldn't generate a clear response."
        
#     except Exception as e:
#         return f"Error generating response: {e}"

# # === Main Chat Function ===
# def chat_with_model(query: str) -> str:
#     """Main chat function with improved logic"""
#     if not query.strip():
#         return "Please ask me something about SJCET Palai."
    
#     # 1️⃣ Try custom Q&A first (fast and accurate)
#     custom_answer = find_custom_answer(query)
#     if custom_answer:
#         return custom_answer
    
#     # 2️⃣ Try RAG if ChromaDB is available
#     if collection:
#         print("🔍 Searching database for relevant information...")
#         context = retrieve_context(query)
        
#         if context:
#             prompt = build_prompt(context, query)
#             print("🤖 Generating response...")
#             return generate_llm_response(prompt)
#         else:
#             return "I couldn't find specific information about that topic in the database."
    
#     # 3️⃣ Fallback message
#     return ("I don't have specific information about that topic. "
#             "You can ask me about the college name, principal, location, or general information about SJCET.")

# # === Enhanced CLI ===
# if __name__ == "__main__":
#     print("\n" + "="*50)
#     print("🎓 SJCET Palai Assistant")
#     print("="*50)
    
#     # Show system status
#     if collection:
#         print("✅ Database connected - Full knowledge available")
#     else:
#         print("⚠️ Database offline - Limited to essential Q&A")
    
#     print("\n💬 Ask me anything about the college (type 'exit' to quit)")
#     print("-" * 50)
    
#     while True:
#         try:
#             user_input = input("\n🧑 You: ").strip()
            
#             if user_input.lower() in {"exit", "quit", "bye"}:
#                 print("\n👋 Goodbye!")
#                 break
                
#             if not user_input:
#                 continue
            
#             response = chat_with_model(user_input)
#             print(f"\n🤖 Assistant: {response}")
            
#         except KeyboardInterrupt:
#             print("\n\n👋 Goodbye!")
#             break
#         except Exception as e:
#             print(f"\n❌ Error: {e}")
# 
# 
# 
# 
# 
# 

## without groq this also works fine 


# from transformers import AutoTokenizer, AutoModelForCausalLM
# from chromadb import PersistentClient
# import torch
# import os
# from Chatbot.llm.custom_qa import find_custom_answer, load_custom_qa  # ✅ load and find

# MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
# CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "vector-database", "chroma_db")
# CHROMA_DB_DIR = os.path.abspath(CHROMA_DB_DIR)
# COLLECTION_NAME = "website_data"

# # === Load Model ===
# print("🚀 Loading model...")
# model = AutoModelForCausalLM.from_pretrained(
#     MODEL_ID,
#     torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
#     device_map="auto",
#     low_cpu_mem_usage=True
# )
# tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
# if tokenizer.pad_token is None:
#     tokenizer.pad_token = tokenizer.eos_token

# # === Connect to ChromaDB ===
# def connect_to_chromadb():
#     try:
#         if not os.path.exists(CHROMA_DB_DIR):
#             print(f"⚠️ ChromaDB directory not found: {CHROMA_DB_DIR}")
#             return None

#         client = PersistentClient(path=CHROMA_DB_DIR)
#         collection = client.get_collection(COLLECTION_NAME)
#         count = collection.count()
#         print(f"📊 Connected to ChromaDB. Collection has {count} documents.")
#         return collection if count > 0 else None
#     except Exception as e:
#         print(f"⚠️ ChromaDB error: {e}")
#         return None

# collection = connect_to_chromadb()

# # === Retrieval Function ===
# def retrieve_context(query, top_k=4, max_chars=1500):
#     if not collection:
#         return ""
#     try:
#         results = collection.query(query_texts=[query], n_results=top_k)
#         docs = results.get('documents', [[]])[0]
#         combined = ""
#         for doc in docs:
#             if len(combined) + len(doc) > max_chars:
#                 combined += doc[:max_chars - len(combined)]
#                 break
#             combined += doc + "\n\n"
#         return combined.strip()
#     except Exception as e:
#         print(f"❌ Retrieval error: {e}")
#         return ""

# # === Prompt Builder ===
# def build_prompt(context, user_input):
#     return f"""Based on the following information about SJCET Palai:

# {context}

# Question: {user_input}
# Answer:"""

# # === LLM Response ===
# def generate_llm_response(prompt):
#     try:
#         inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1600).to(model.device)
#         outputs = model.generate(
#             **inputs,
#             max_new_tokens=200,
#             do_sample=True,
#             temperature=0.4,
#             top_p=0.9,
#             pad_token_id=tokenizer.eos_token_id,
#             eos_token_id=tokenizer.eos_token_id,
#             repetition_penalty=1.1
#         )
#         return tokenizer.decode(
#             outputs[0][inputs["input_ids"].shape[1]:],
#             skip_special_tokens=True
#         ).strip()
#     except Exception as e:
#         return f"⚠️ Error generating response: {e}"

# # === Main Chat ===
# def chat_with_model(query):
#     if not query.strip():
#         return "Please ask me something about SJCET Palai."

#     # 🔄 Reload custom Q&A so updates in JSON are reflected immediately
#     load_custom_qa()

#     # 1️⃣ Try custom Q&A first
#     custom_answer = find_custom_answer(query)
#     if custom_answer:
#         return custom_answer

#     # 2️⃣ Try RAG
#     if collection:
#         context = retrieve_context(query)
#         if context:
#             return generate_llm_response(build_prompt(context, query))
#         else:
#             return "I couldn't find that in the database."

#     # 3️⃣ Fallback
#     return "I don't have specific information on that topic."

# if __name__ == "__main__":
#     print("\n🎓 SJCET Palai Assistant")
#     print("Type 'exit' to quit.\n")
#     while True:
#         try:
#             q = input("🧑 You: ").strip()
#             if q.lower() in {"exit", "quit"}:
#                 print("\n👋 Goodbye!")
#                 break
#             print(f"\n🤖 Assistant: {chat_with_model(q)}\n")
#         except KeyboardInterrupt:
#             print("\n\n👋 Goodbye!")
#             break
#         except Exception as e:
#             print(f"\n❌ Error: {e}")



## with groq 
import os
from dotenv import load_dotenv
from groq import Groq
from chromadb import PersistentClient
from Chatbot.llm.custom_qa import find_custom_answer, load_custom_qa  # ✅ load and find


load_dotenv()
# === Config ===
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "vector-database", "chroma_db")
CHROMA_DB_DIR = os.path.abspath(CHROMA_DB_DIR)
COLLECTION_NAME = "website_data"

# === Init Groq Client ===
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# === Connect to ChromaDB ===
def connect_to_chromadb():
    try:
        if not os.path.exists(CHROMA_DB_DIR):
            print(f"⚠️ ChromaDB directory not found: {CHROMA_DB_DIR}")
            return None

        client_db = PersistentClient(path=CHROMA_DB_DIR)
        collection = client_db.get_collection(COLLECTION_NAME)
        count = collection.count()
        print(f"📊 Connected to ChromaDB. Collection has {count} documents.")
        return collection if count > 0 else None
    except Exception as e:
        print(f"⚠️ ChromaDB error: {e}")
        return None

collection = connect_to_chromadb()

# === Retrieval Function ===
def retrieve_context(query, top_k=4, max_chars=1500):
    if not collection:
        return ""
    try:
        results = collection.query(query_texts=[query], n_results=top_k)
        docs = results.get('documents', [[]])[0]
        combined = ""
        for doc in docs:
            if len(combined) + len(doc) > max_chars:
                combined += doc[:max_chars - len(combined)]
                break
            combined += doc + "\n\n"
        return combined.strip()
    except Exception as e:
        print(f"❌ Retrieval error: {e}")
        return ""

# === Prompt Builder ===
def build_prompt(context, user_input):
    return f"""Based on the following information about SJCET Palai:

{context}

Question: {user_input}
Answer:"""

# === LLM Response (Groq Streaming) ===
def generate_llm_response(prompt):
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",  # ✅ Groq model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            top_p=0.9,
            max_tokens=300,
            stream=True
        )

        response_text = ""
        for chunk in completion:
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)  # Stream to console
                response_text += content
        print()  # final newline
        return response_text.strip()

    except Exception as e:
        return f"⚠️ Error generating response: {e}"

# === Main Chat ===
def chat_with_model(query):
    if not query.strip():
        return "Please ask me something about SJCET Palai."

    # 🔄 Reload custom Q&A so updates in JSON are reflected immediately
    load_custom_qa()

    # 1️⃣ Try custom Q&A first
    custom_answer = find_custom_answer(query)
    if custom_answer:
        return custom_answer

    # 2️⃣ Try RAG
    if collection:
        context = retrieve_context(query)
        if context:
            return generate_llm_response(build_prompt(context, query))
        else:
            return "I couldn't find that in the database."

    # 3️⃣ Fallback
    return "I don't have specific information on that topic."

if __name__ == "__main__":
    print("\n🎓 SJCET Palai Assistant (Groq-powered)")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            q = input("🧑 You: ").strip()
            if q.lower() in {"exit", "quit"}:
                print("\n👋 Goodbye!")
                break
            print("\n🤖 Assistant: ", end="")
            answer = chat_with_model(q)
            if answer:  # in case custom_answer returned text
                print(answer)
            print()
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
