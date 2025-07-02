import streamlit as st
from qa_test import run_qa_pipeline

st.set_page_config(page_title="CodeWiz Assistant", page_icon="🤖")
st.title("🤖 CodeWiz Assistant")

# Persona selector
user_type = st.radio(
    "What role describes you best?",
    ["Franchisee", "Support/Technical Team", "Management/Leadership"],
    horizontal=True
)

st.markdown("""
**Ask a question based on the technical documents:**

*Example:* What are the suggested improvements mentioned in the tech stack mapping?
""")

query = st.text_input(
    label="",
    placeholder="Type your question here...",
    label_visibility="collapsed"
)

if st.button("Send") and query:
    with st.spinner("Retrieving answer..."):
        response = run_qa_pipeline(query, user_type=user_type.lower())

    st.markdown("###  Answer:")
    st.write(response.get("result", "No answer found."))

    # Only show chunks and source files for internal members
    if user_type.lower() in ["support/technical team", "management/leadership"]:
        st.markdown("---")
        with st.expander("🔍 Chunks used for this answer"):
            for i, chunk in enumerate(response.get("chunks", [])):
                st.markdown(f"**Chunk {i+1}:**\n{chunk}")

        # Show source files in a separate toggle
        if "sources" in response and response["sources"]:
            with st.expander("📄 Source files"):
                for src in response["sources"]:
                    st.markdown(f"- {src}")

st.markdown("""
---
*This is an MVP interface using local FAISS and GPT-4 Turbo with persona-adapted answers.*
""")
