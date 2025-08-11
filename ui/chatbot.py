import streamlit as st
from transformers import AutoTokenizer, AutoModelForCausalLM
from chromadb import PersistentClient
import torch
import os

# === Config ===
MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
CHROMA_DB_DIR = "../vector-database/chroma_db"
COLLECTION_NAME = "website_data"

# === Load Model & Tokenizer ===
@st.cache_resource
def load_model_and_tokenizer():
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        low_cpu_mem_usage=True
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer

# === Connect to ChromaDB ===
@st.cache_resource
def connect_to_chromadb():
    try:
        client = PersistentClient(path=CHROMA_DB_DIR)
        collection = client.get_collection(COLLECTION_NAME)
        return collection
    except Exception as e:
        st.error(f"❌ Error connecting to ChromaDB: {e}")
        return None

model, tokenizer = load_model_and_tokenizer()
collection = connect_to_chromadb()

# === Retrieval Function ===
def retrieve_context(query: str, top_k: int = 4, max_chars: int = 1500):
    if not collection:
        return "", []

    try:
        results = collection.query(query_texts=[query], n_results=top_k)
        docs = results.get('documents', [[]])[0] if results.get('documents') else []
        metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else []
        
        combined = ""
        chunks_info = []

        for i, doc in enumerate(docs):
            meta = metadatas[i] if i < len(metadatas) else {}
            chunks_info.append({
                "index": i + 1,
                "title": meta.get("title", "No title"),
                "content": doc,
                "length": len(doc)
            })

            if doc and doc.strip():
                if len(combined) + len(doc) > max_chars:
                    remaining_chars = max_chars - len(combined)
                    if remaining_chars > 100:
                        combined += doc[:remaining_chars].strip() + "\n\n"
                    break
                combined += doc.strip() + "\n\n"

        return combined.strip(), chunks_info
    except Exception as e:
        st.error(f"❌ Error during retrieval: {e}")
        return "", []

# === Model Generation ===
def generate_answer(context: str, query: str):
    prompt = f"""Context from website:
{context}

Question: {query}
Answer: Based on the context above,"""
    
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1500,
        padding=True
    ).to(model.device)

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
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return response.strip()

# === Streamlit UI ===
st.set_page_config(page_title="RAG Assistant", page_icon="🤖", layout="wide")

st.title("💬 RAG Chat Assistant")
st.write("Ask a question, and the model will answer using retrieved website data.")

query = st.text_input("Enter your question:")
context_only = st.checkbox("Context-Only Mode (No AI generation)", value=False)

if query:
    with st.spinner("🔍 Retrieving context..."):
        context, chunks_info = retrieve_context(query)

    if chunks_info:
        with st.expander("📄 Retrieved Chunks"):
            for chunk in chunks_info:
                st.markdown(f"**Chunk {chunk['index']} - {chunk['title']}**")
                st.text_area(
                    label=f"Chunk {chunk['index']} Content",
                    value=chunk['content'],
                    height=120
                )

    if not context:
        st.warning("No relevant context found.")
    else:
        if context_only:
            st.subheader("📄 Retrieved Context")
            st.write(context)
        else:
            with st.spinner("🤖 Generating answer..."):
                answer = generate_answer(context, query)
            st.subheader("🤖 Answer")
            st.write(answer)
