# # ui/chatbot.py
# import sys
# import os

# # Ensure parent directory is in Python path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from llm.llm import chat_with_model, retrieve_context

# import streamlit as st

# st.set_page_config(page_title="Chat Assistant", page_icon="🤖", layout="wide")

# st.title("💬 Chat Assistant")
# st.write("Ask a question and get answers from our knowledge base.")

# query = st.text_input("Enter your question:")
# show_context = st.checkbox("Show retrieved context", value=False)

# if query:
#     with st.spinner("🤖 Thinking..."):
#         answer = chat_with_model(query)

#     st.subheader("Answer")
#     st.write(answer)

#     if show_context:
#         with st.expander("📄 Retrieved Context"):
#             context = retrieve_context(query)
#             st.write(context if context else "No relevant context found.")


import sys
import os

# Ensure parent directory is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm.llm import chat_with_model, retrieve_context

import streamlit as st

st.set_page_config(page_title="Chat Assistant", page_icon="🤖", layout="wide")

st.title("💬 Chat Assistant")
st.write("Chat with our assistant and get answers from the knowledge base.")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display chat history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input field
if prompt := st.chat_input("Ask me anything..."):
    # Add user message to history
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking..."):
            answer = chat_with_model(prompt)
            st.markdown(answer)

    # Save assistant message to history
    st.session_state["messages"].append({"role": "assistant", "content": answer})

# Optional: Toggle to show retrieved context
if st.checkbox("Show retrieved context"):
    if st.session_state.get("messages"):
        last_user_msg = next((m["content"] for m in reversed(st.session_state["messages"]) if m["role"] == "user"), None)
        if last_user_msg:
            context = retrieve_context(last_user_msg)
            with st.expander("📄 Retrieved Context"):
                st.write(context if context else "No relevant context found.")
