from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from pathlib import Path
import os
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Paths
DOCS_FOLDER = "codewizAIassistant/data/raw"
INDEX_PATH = "codewiz_ai_assistant/vectorstore"

def load_documents_from_folder(folder_path: str) -> list[Document]:
    docs = []
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        logging.error(f"❌ The provided path is not a valid directory: {folder_path}")
        return docs

    for file_path in folder.glob("*.pdf"):
        try:
            loader = UnstructuredPDFLoader(str(file_path))
            loaded = loader.load()

            for doc in loaded:
                doc.metadata.update({
                    "source_pdf": file_path.name,
                    "status": "verde" if "novo" in file_path.name.lower() else "azul",
                    "user_type": "franchisee" if "franchisee" in file_path.name.lower() else "staff",
                    "bucket": "zoho" if "zoho" in file_path.name.lower() else "general"
                })

            docs.extend(loaded)
            logging.info(f"✅ Loaded {len(loaded)} documents from {file_path.name}")

        except Exception as e:
            logging.error(f"❌ Error loading file {file_path.name}: {e}")

    return docs

def index_documents(docs: list[Document], persist_path=INDEX_PATH):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    chunks = text_splitter.split_documents(docs)
    logging.info(f"🧩 Total chunks after splitting: {len(chunks)}")

    # Count per document for detailed logging
    doc_counter = defaultdict(int)
    for chunk in chunks:
        key = (
            chunk.metadata.get("source_pdf", "unknown"),
            chunk.metadata.get("bucket", "misc"),
            chunk.metadata.get("status", "unspecified"),
            chunk.metadata.get("user_type", "general")
        )
        doc_counter[key] += 1

    for (source_pdf, bucket, status, user_type), count in doc_counter.items():
        logging.info(
            f"📌 Indexed {count} chunks from \"{source_pdf}\" | "
            f"bucket: {bucket} | user_type: {user_type} | status: {status}"
        )

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    if os.path.exists(persist_path):
        db = FAISS.load_local(persist_path, embeddings, allow_dangerous_deserialization=True)
        db.add_documents(chunks)
    else:
        db = FAISS.from_documents(chunks, embeddings)

    # Save the FAISS index
    db.save_local(persist_path)
    logging.info(f"✅ FAISS index saved to: {persist_path}")

if __name__ == "__main__":
    documents = load_documents_from_folder(DOCS_FOLDER)
    logging.info(f"📚 Total documents loaded: {len(documents)}")
    index_documents(documents)
