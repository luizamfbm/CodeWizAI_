import os
import shutil
import csv
import logging

from load_documents import load_documents_from_folder
from preprocess import preprocess_documents, advanced_deduplication
from generate_embeddings import index_documents

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DOCS_PATH = "data/raw"  # Use only one folder
CSV_OUTPUT_PATH = "data_inventoryLUIZA.csv"

CODEWIZ_TECH_STACK = [
    "python", "streamlit", "langchain", "openai", "chromadb", "sqlite", "docker", "azure", "git"
]

def is_question_in_tech_stack(question):
    return any(stack in question.lower() for stack in CODEWIZ_TECH_STACK)

def answer_question(question, retriever, similarity_threshold=0.6):
    if not is_question_in_tech_stack(question):
        return "I don't know", None, None

    answer, retrieved_chunks, similarity_score = retriever(question)

    if not retrieved_chunks or len(retrieved_chunks) == 0:
        return "I don't know", retrieved_chunks, similarity_score

    if not answer or (similarity_score is not None and similarity_score < similarity_threshold):
        return "I don't know", retrieved_chunks, similarity_score

    return answer, retrieved_chunks, similarity_score

def gerar_csv_inventario(docs, output_path=CSV_OUTPUT_PATH):
    """
    Generates a CSV with inventory information according to the requirements:
    - Source file name
    - Bucket (topic)
    - Applied transformations
    """
    fieldnames = ["source_file", "bucket", "transformations_applied"]

    with open(output_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for doc in docs:
            try:
                metadata = doc.metadata

                transformations = []
                if metadata.get("converted", False):
                    transformations.append("converted to PDF")
                transformations.append("chunked")
                if metadata.get("deduplicated", False):
                    transformations.append("duplicated chunks removed")
                transformations.append("embedded")

                writer.writerow({
                    "source_file": metadata.get("source_pdf", ""),
                    "bucket": metadata.get("bucket", ""),
                    "transformations_applied": ", ".join(transformations)
                })
            except Exception as e:
                logging.error(f"❌ Error writing CSV line: {e}")

    logging.info(f"✅ Inventory CSV generated at: {output_path}")

# Add at the beginning of your main.py or in a utility module

def buscar_chunks_relevantes(question):
    # Use the FAISS retriever
    return retriever.get_relevant_documents(question)

def calcular_similaridade(question, chunk):
    # Optional: implement a real similarity function, or use FAISS's if available
    # For simplicity, return 1.0 if chunk was returned by the retriever
    return 1.0

def gerar_resposta(question, chunks):
    if not chunks:
        return None
    # Here, generate the answer based only on the chunks.
    # Safe example:
    context = "\n".join([chunk.page_content for chunk in chunks if hasattr(chunk, "page_content")])
    if not context.strip():
        return None
    # Only call the model if there is context!
    # return modelo_gpt(question, context=context)
    return "YOUR ANSWER LOGIC"

# Example of robust retriever
def retriever(question):
    retrieved_chunks = buscar_chunks_relevantes(question)
    if not retrieved_chunks:
        return None, [], None

    similarity_score = calcular_similaridade(question, retrieved_chunks[0])
    if similarity_score < 0.6:
        return None, retrieved_chunks, similarity_score

    answer = gerar_resposta(question, retrieved_chunks)
    return answer, retrieved_chunks, similarity_score

if __name__ == "__main__":
    # 1️⃣ Load documents
    docs = load_documents_from_folder(DOCS_PATH)
    docs = [doc for doc in docs if doc is not None]
    logging.info(f"📚 Documents loaded and filtered: {len(docs)}")

    if not docs:
        logging.warning("⚠️ No valid documents to process. Exiting.")
        exit(0)

    # 2️⃣ Preprocess documents
    chunks = preprocess_documents(docs)
    chunks = [chunk for chunk in chunks if chunk is not None]
    logging.info(f"🧩 Chunks after preprocessing: {len(chunks)}")

    if not chunks:
        logging.warning("⚠️ No chunks generated after preprocessing. Exiting.")
        exit(0)

    # 3️⃣ Deduplicate
    final_chunks = advanced_deduplication(chunks)
    final_chunks = [chunk for chunk in final_chunks if chunk is not None]
    logging.info(f"🧩 Chunks after deduplication: {len(final_chunks)}")

    # Extra defensive check
    final_chunks = [
        chunk for chunk in final_chunks
        if hasattr(chunk, "page_content") and chunk.page_content
    ]

    if not final_chunks:
        logging.warning("⚠️ No valid chunks to index. Exiting.")
        exit(0)

    # 4️⃣ Generate inventory (now using the processed chunks!)
    gerar_csv_inventario(final_chunks)

    # 5️⃣ Index
    try:
        index_documents(final_chunks)
    except Exception as e:
        logging.error(f"❌ Error during indexing: {e}")
        exit(1)

    logging.info("✅ Full pipeline successfully executed.")


