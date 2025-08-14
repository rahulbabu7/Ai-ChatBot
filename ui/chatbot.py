# ui/chatbot.py
import sys
import os

# Ensure parent directory is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm.llm import chat_with_model, retrieve_context

import streamlit as st

st.set_page_config(page_title="Chat Assistant", page_icon="🤖", layout="wide")

st.title("💬 Chat Assistant")
st.write("Ask a question and get answers from our knowledge base.")

query = st.text_input("Enter your question:")
show_context = st.checkbox("Show retrieved context", value=False)

if query:
    with st.spinner("🤖 Thinking..."):
        answer = chat_with_model(query)

    st.subheader("Answer")
    st.write(answer)

    if show_context:
        with st.expander("📄 Retrieved Context"):
            context = retrieve_context(query)
            st.write(context if context else "No relevant context found.")
