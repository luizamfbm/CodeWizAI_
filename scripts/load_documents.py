from pathlib import Path
import logging
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredPDFLoader
from langchain.schema import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_documents_from_folder(folder_path: str) -> list[Document]:
    docs = []
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        logging.error(f"❌ The provided path is not a valid directory: {folder_path}")
        return docs

    for file_path in folder.glob("*.pdf"):
        try:
            # try PyMuPDFLoader first
            loader = PyMuPDFLoader(str(file_path))
            loaded = loader.load()
            
            # check if the text is empty (e.g., image-based PDFs)
            if all(not doc.page_content.strip() for doc in loaded):
                logging.warning(f"⚠️ {file_path.name} seems image-based, trying OCR fallback...")
                loader_ocr = UnstructuredPDFLoader(str(file_path))
                loaded = loader_ocr.load()
            
            for doc in loaded:
                if doc is not None:
                    doc.metadata.update({
                        "source_pdf": file_path.name,
                        "status": "green" if "novo" in file_path.name.lower() else "blue",
                        "user_type": "franchisee" if "franchisee" in file_path.name.lower() else "staff",
                        "bucket": "",
                        "converted": True
                    })
                    docs.append(doc)
                else:
                    logging.warning(f"⚠️ Loader returned None for {file_path.name}")
            
            logging.info(f"✅ Loaded {len(loaded)} document(s) from {file_path.name}")
        
        except Exception as e:
            logging.error(f"❌ Error loading file {file_path.name}: {e}")

    return docs

if __name__ == "__main__":
    folder_path = "data/raw"
    all_docs = load_documents_from_folder(folder_path)
    logging.info(f"📚 Total documents loaded: {len(all_docs)}")

    for doc in all_docs:
        try:
            preview = doc.page_content[:200].replace("\n", " ")
            logging.info(
                f"📄 {doc.metadata['source_pdf']} | "
                f"👥 Type: {doc.metadata['user_type']} | "
                f"Status: {doc.metadata['status']} | "
                f"Preview: {preview}..."
            )
        except Exception as e:
            logging.error(f"❌ Error previewing document metadata: {e}")
