from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import os
import csv
from datetime import datetime
from main import answer_question, gerar_resposta

# Paths
INDEX_PATH = "codewiz_ai_assistant/vectorstore"
LOG_FILE = "logs/qa_logs.csv"

# Ensure CSV header
if not os.path.exists(LOG_FILE):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "user_type", "question", "answer"])

# Embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
db = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)

# GPT-4 Turbo
llm = ChatOpenAI(
    model="gpt-4-turbo",
    temperature=0.1,
    max_tokens=512
)

# Retriever with optimized settings
retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 8})

# Prompt with persona
custom_prompt = PromptTemplate(
    input_variables=["context", "question", "user_type"],
    template="""
You are answering on behalf of CodeWiz.

Adapt your tone and detail level to match the {user_type} persona:
- Management/Leadership: high-level, strategic, focus on business decisions
- Support/Technical Team: technical, detailed, with examples and process explanation
- Franchisee: practical, clear steps, day-to-day instructions

Use only the provided context to answer. If the answer is incomplete or unclear, summarize what is known, mention what is missing, and do not invent details.

**When deciding which context to trust and present:**
- prefer documents with higher status (green > blue > purple)
- prefer documents with more recent timestamps if available
- if conflicting information exists, select chunks with higher confidence and clearer source
- ignore irrelevant or outdated chunks

If no answer is found in the context, reply with:
"I couldn’t find a clear answer based on current documentation."

Context:
{context}

Question: {question}
Answer:
"""
)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def save_log_csv(user_type, question, answer):
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_type,
            question,
            answer
        ])

def custom_retriever(question):
    retrieved_chunks = db.similarity_search(question)
    if not retrieved_chunks:
        return None, [], None
    similarity_score = 1.0  # or calculate for real
    answer = gerar_resposta(question, retrieved_chunks)
    return answer, retrieved_chunks, similarity_score

def run_qa_pipeline(question, user_type="general"):
    if not question:
        return {"result": "❗ Please enter a valid question.", "chunks": []}

    try:
        docs = retriever.get_relevant_documents(question)

        if any(term in question.lower() for term in ["template", "follow-up", "flup", "email", "text", "message"]):
            extra_queries = [
                "email template content",
                "follow up message",
                "trial class communication",
                "parent communication templates"
            ]
            for extra_query in extra_queries:
                extra_docs = retriever.get_relevant_documents(extra_query)
                existing_content = [d.page_content for d in docs]
                for doc in extra_docs:
                    if doc.page_content not in existing_content and len(docs) < 8:
                        docs.append(doc)

        context = format_docs(docs)

        chain = (
            RunnablePassthrough.assign(context=lambda x: context)
            | custom_prompt
            | llm
            | StrOutputParser()
        )

        result = chain.invoke({
            "question": question,
            "user_type": user_type,
            "context": context
        })

        # Do not include source_note in the answer anymore!
        final_answer = result

        save_log_csv(user_type, question, final_answer)

        return {
            "result": final_answer,
            "chunks": [doc.page_content for doc in docs],
            "sources": [doc.metadata.get("source_pdf", "unknown") for doc in docs]
        }
    except Exception as e:
        print(f"❌ Error in LCEL pipeline: {str(e)}")
        return run_simple_qa_pipeline(question, user_type)

def run_simple_qa_pipeline(question: str, user_type: str = "franchisee") -> dict:
    if not question:
        return {"result": "❗ Please enter a valid question.", "chunks": []}

    try:
        simple_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are answering on behalf of CodeWiz. Keep your language clear and professional.

Use only the context below to answer the question. If the answer is not in the context, say:
"I don't know."

Context:
{context}

Question: {question}
Answer:
"""
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,  # <-- now it's the correct object!
            chain_type="stuff",
            chain_type_kwargs={"prompt": simple_prompt},
            return_source_documents=True,
            input_key="query"
        )

        resposta = qa_chain.invoke({"query": question})
        base_answer = resposta.get("result", "❗ No answer found.")

        if user_type.lower() == "franchisee":
            adapted_answer = f"🏪 For franchisees: {base_answer}"
        elif user_type.lower() in ["staff", "support", "technical"]:
            adapted_answer = f"👥 For staff: {base_answer}"
        else:
            adapted_answer = base_answer

        chunks = []
        sources = set()
        for doc in resposta.get("source_documents", []):
            # Collect chunk content and sources
            if hasattr(doc, "page_content"):
                chunks.append(doc.page_content)
            if hasattr(doc, "metadata"):
                sources.add(doc.metadata.get("source_pdf", "unknown"))
        # Optionally, you could add a source_note here if needed
        final_answer = adapted_answer

        save_log_csv(user_type, question, final_answer)

        return {
            "result": final_answer,
            "chunks": chunks,
            "sources": list(sources)
        }

    except Exception as e:
        print(f"❌ Error in simple pipeline: {str(e)}")
        return {"result": f"❌ Error: {str(e)}", "chunks": []}

def debug_search(question: str):
    print(f"\n🔍 DEBUG: Searching for '{question}'")
    docs = retriever.get_relevant_documents(question)
    print(f"📊 Found {len(docs)} documents")
    for i, doc in enumerate(docs[:3]):
        print(f"\n📄 Doc {i+1}")
        print(f"Source: {doc.metadata.get('source_pdf', 'Unknown')}")
        print(f"Preview: {doc.page_content[:200]}...")
    return docs

def gerar_resposta(question, chunks):
    if not chunks:
        return None
    context = "\n".join([chunk.page_content for chunk in chunks if hasattr(chunk, "page_content")])
    if not context.strip():
        return None
    # Call the model here, if you want
    # return llm.invoke({"question": question, "context": context})
    return context  # or your answer logic

if __name__ == "__main__":
    print("🤖 CodeWiz AI Assistant - Testing Mode")
    while True:
        question = input("\n❓ Ask your question (or 'quit' to exit): ").strip()
        if question.lower() in ["quit", "exit", "q"]:
            break
        if not question:
            continue
        user_type = input("👤 User type [franchisee/staff/debug]: ").strip().lower()
        if user_type == "debug":
            debug_search(question)
            continue
        if user_type not in ["franchisee", "staff"]:
            user_type = "franchisee"
            print("⚠️ Invalid user type, defaulting to 'franchisee'")
        print("\n🔄 Processing...")
        try:
            resposta = run_qa_pipeline(question, user_type)
            print("\nAnswer:\n", resposta["result"])
            if resposta.get("chunks"):
                print(f"\n🔍 Found {len(resposta['chunks'])} relevant chunks:")
                for i, chunk in enumerate(resposta["chunks"][:3]):
                    print(f"\n🔹 Chunk {i+1}:\n{chunk[:300]}...")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            try:
                resposta = run_simple_qa_pipeline(question, user_type)
                print("\n Answer (fallback):\n", resposta["result"])
            except Exception as e2:
                print(f"❌ Complete failure: {e2}")
