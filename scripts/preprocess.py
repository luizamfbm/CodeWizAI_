from pathlib import Path
import logging
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import List, Dict, Set
from collections import defaultdict
import re
import json
import streamlit as st

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🗂️ Bucket system based on ZOHO business context
class ZOHOBucketClassifier:
    def __init__(self):
        # Buckets defined based on meeting feedback
        self.buckets = {
            # Types of leads and how they enter the system
            "lead_sources": {
                "keywords": ["phone call", "inbound call", "form submission", "book me", "iclass pro", "manually created"],
                "patterns": [
                    r"lead.*(?:phone|call|inbound)",
                    r"(?:form|booking|book me)",
                    r"manually.*(?:created|added)"
                ],
                "context": "lead generation and entry points"
            },
            
            # Sales process - from lead to payment
            "sales_process": {
                "keywords": ["trial class", "consultation", "follow-up", "no show", "payment", "conversion", "enrollment"],
                "patterns": [
                    r"trial.*class",
                    r"follow.*up",
                    r"no.*show",
                    r"sales.*process",
                    r"conversion.*rate"
                ],
                "context": "sales pipeline and customer journey"
            },
            
            # Lead status and workflows
            "lead_status": {
                "keywords": ["new lead", "qualified", "contacted", "scheduled", "enrolled", "lost", "nurturing"],
                "patterns": [
                    r"lead.*status",
                    r"qualified.*lead",
                    r"scheduled.*(?:trial|class)",
                    r"enrolled.*student"
                ],
                "context": "lead qualification and status tracking"
            },
            
            # CRM workflows and automations
            "crm_workflows": {
                "keywords": ["zoho", "workflow", "automation", "trigger", "assignment", "routing"],
                "patterns": [
                    r"workflow.*(?:automation|trigger)",
                    r"crm.*(?:process|system)",
                    r"automatic.*(?:assignment|routing)"
                ],
                "context": "CRM system workflows and automations"
            },
            
            # Communication and follow-up
            "communication": {
                "keywords": ["email", "sms", "call", "message", "notification", "reminder"],
                "patterns": [
                    r"(?:email|sms).*(?:campaign|sequence)",
                    r"follow.*up.*(?:call|email)",
                    r"automated.*(?:reminder|notification)"
                ],
                "context": "customer communication and follow-up"
            },
            
            # Franchisee-specific processes
            "franchisee_operations": {
                "keywords": ["franchisee", "location", "staff", "instructor", "schedule", "class management"],
                "patterns": [
                    r"franchisee.*(?:process|operation)",
                    r"staff.*(?:training|management)",
                    r"class.*(?:schedule|management)"
                ],
                "context": "franchisee-specific operations and processes"
            },
            
            # Technical support and troubleshooting
            "technical_support": {
                "keywords": ["error", "bug", "troubleshoot", "technical issue", "system problem", "integration"],
                "patterns": [
                    r"technical.*(?:issue|problem)",
                    r"system.*(?:error|bug)",
                    r"integration.*(?:problem|issue)"
                ],
                "context": "technical support and system issues"
            },
            
            # Reporting and analytics
            "reporting": {
                "keywords": ["report", "analytics", "metrics", "dashboard", "kpi", "performance"],
                "patterns": [
                    r"(?:report|analytics).*(?:generation|dashboard)",
                    r"performance.*(?:metrics|kpi)",
                    r"conversion.*(?:rate|metrics)"
                ],
                "context": "reporting and performance analytics"
            }
        }
        
        # Mapping user_type to relevant buckets
        self.user_type_buckets = {
            "franchisee": ["lead_sources", "sales_process", "franchisee_operations", "communication"],
            "staff": ["crm_workflows", "technical_support", "lead_status", "communication"],
            "leadership": ["reporting", "sales_process", "crm_workflows", "franchisee_operations"]
        }
    
    def classify_chunk(self, text: str, user_type: str = "general") -> Dict[str, float]:
        """
        Classifies a text chunk into multiple buckets with confidence scores
        """
        scores = {}
        text_lower = text.lower()
        
        for bucket_name, bucket_info in self.buckets.items():
            score = 0.0
            
            # Score based on keywords
            keyword_matches = sum(1 for keyword in bucket_info["keywords"] 
                                if keyword.lower() in text_lower)
            if keyword_matches > 0:
                score += (keyword_matches / len(bucket_info["keywords"])) * 0.6
            
            # Score based on regex patterns
            pattern_matches = sum(1 for pattern in bucket_info["patterns"] 
                                if re.search(pattern, text_lower))
            if pattern_matches > 0:
                score += (pattern_matches / len(bucket_info["patterns"])) * 0.4
            
            # Boost for buckets relevant to user_type
            if user_type in self.user_type_buckets:
                if bucket_name in self.user_type_buckets[user_type]:
                    score *= 1.2
            
            scores[bucket_name] = score
        
        return scores
    
    def get_primary_bucket(self, text: str, user_type: str = "general", threshold: float = 0.1) -> str:
        """
        Returns the primary bucket with the highest score
        """
        scores = self.classify_chunk(text, user_type)
        
        if not scores or max(scores.values()) < threshold:
            return "misc"
        
        return max(scores, key=scores.get)
    
    def get_multiple_buckets(self, text: str, user_type: str = "general", threshold: float = 0.1) -> List[str]:
        """
        Returns all buckets above the threshold
        """
        scores = self.classify_chunk(text, user_type)
        
        return [bucket for bucket, score in scores.items() if score >= threshold]

# Improved function to detect document type based on filename
def detect_document_type(filename: str) -> Dict[str, str]:
    """
    Detects the document type and other metadata based on the file name
    """
    filename_lower = filename.lower()
    
    # Detect user_type
    user_type = "general"
    if any(word in filename_lower for word in ["franchisee", "franchise"]):
        user_type = "franchisee"
    elif any(word in filename_lower for word in ["staff", "support", "technical"]):
        user_type = "staff"
    elif any(word in filename_lower for word in ["leadership", "management", "executive"]):
        user_type = "leadership"
    
    # Detect status (priority)
    status = "blue"  # default
    if any(word in filename_lower for word in ["novo", "new", "latest", "current"]):
        status = "green"
    elif any(word in filename_lower for word in ["old", "archived", "deprecated"]):
        status = "purple"
    
    # Detect document type
    doc_type = "general"
    if any(word in filename_lower for word in ["transcript", "call", "meeting"]):
        doc_type = "transcript"
    elif any(word in filename_lower for word in ["workflow", "process", "mapping"]):
        doc_type = "process_doc"
    elif any(word in filename_lower for word in ["manual", "guide", "instruction"]):
        doc_type = "manual"
    elif any(word in filename_lower for word in ["report", "analytics", "metrics"]):
        doc_type = "report"
    
    return {
        "user_type": user_type,
        "status": status,
        "doc_type": doc_type
    }

def load_documents_from_folder(folder_path: str) -> List[Document]:
    """
    Loads documents with improved classification
    """
    docs = []
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        logging.error(f"❌ The provided path is not a valid directory: {folder_path}")
        return docs
    
    for file_path in folder.glob("*.pdf"):
        try:
            loader = PyMuPDFLoader(str(file_path))
            loaded = loader.load()
            
            # Detect file metadata
            file_metadata = detect_document_type(file_path.name)
            
            for doc in loaded:
                if doc is not None:
                    doc.metadata.update({
                        "source_pdf": file_path.name,
                        "status": file_metadata["status"],
                        "user_type": file_metadata["user_type"],
                        "doc_type": file_metadata["doc_type"],
                        "bucket": "",  # Will be filled in preprocessing
                        "converted": True,
                        "file_size": file_path.stat().st_size,
                        "load_timestamp": str(Path(file_path).stat().st_mtime)
                    })
                    docs.append(doc)
                else:
                    logging.warning(f"⚠️ Loader returned None for {file_path.name}")
            
            logging.info(f"✅ Loaded {len(loaded)} document(s) from {file_path.name}")
            
        except Exception as e:
            logging.error(f"❌ Error loading file {file_path.name}: {e}")
    
    return docs

def redact_sensitive_info(text: str) -> str:
    """
    Removes sensitive information from text
    """
    # Redact emails
    text = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[REDACTED_EMAIL]', text)
    
    # Redact phone numbers (more comprehensive)
    text = re.sub(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', '[REDACTED_PHONE]', text)
    text = re.sub(r'\b\d{2,4}[-.\s]?\d{4,5}[-.\s]?\d{4}\b', '[REDACTED_PHONE]', text)
    
    # Redact names (more sophisticated)
    text = re.sub(r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b', '[REDACTED_NAME]', text)
    
    # Redact possible IDs/codes
    text = re.sub(r'\b[A-Z]{2,}\d{4,}\b', '[REDACTED_ID]', text)
    
    return text

def preprocess_documents(documents: List[Document]) -> List[Document]:
    """
    Improved preprocessing with smart bucket classification
    """
    classifier = ZOHOBucketClassifier()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # Increased for more context
        chunk_overlap=75,  # Higher overlap to preserve context
        separators=["\n\n", "\n", ".", "!", "?", " ", ""]
    )
    
    processed_chunks = []
    
    for doc in documents:
        if doc is None or not hasattr(doc, "page_content") or doc.page_content is None:
            logging.warning("⚠️ Skipping invalid document")
            continue
        
        # Redact sensitive information
        clean_content = redact_sensitive_info(doc.page_content)
        
        # Split into chunks
        chunks = text_splitter.split_text(clean_content)
        
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Skip very small chunks
                continue
            
            # Classify the chunk
            user_type = doc.metadata.get("user_type", "general")
            primary_bucket = classifier.get_primary_bucket(chunk, user_type)
            all_buckets = classifier.get_multiple_buckets(chunk, user_type)
            bucket_scores = classifier.classify_chunk(chunk, user_type)
            
            metadata = {
                "chunk_index": i,
                "bucket": primary_bucket,
                "all_buckets": all_buckets,
                "bucket_scores": bucket_scores,
                "confidence": max(bucket_scores.values()) if bucket_scores else 0.0,
                "source_pdf": doc.metadata.get("source_pdf", "unknown"),
                "status": doc.metadata.get("status", "blue"),
                "user_type": user_type,
                "doc_type": doc.metadata.get("doc_type", "general"),
                "converted": doc.metadata.get("converted", False),
                "deduplicated": False,
                "chunk_length": len(chunk),
                "chunk_words": len(chunk.split())
            }
            
            processed_chunks.append(Document(page_content=chunk, metadata=metadata))
    
    logging.info(f"✅ Total processed chunks: {len(processed_chunks)}")
    
    # Log bucket statistics
    bucket_stats = defaultdict(int)
    for chunk in processed_chunks:
        bucket_stats[chunk.metadata["bucket"]] += 1
    
    logging.info("📊 Bucket distribution:")
    for bucket, count in sorted(bucket_stats.items()):
        logging.info(f"  {bucket}: {count} chunks")
    
    return processed_chunks

def advanced_deduplication(chunks: List[Document]) -> List[Document]:
    """
    More sophisticated deduplication considering context and relevance
    """
    priority_map = {"green": 3, "blue": 2, "purple": 1}
    chunk_groups = defaultdict(list)
    
    # Group similar chunks
    for chunk in chunks:
        if chunk is None or not hasattr(chunk, "page_content"):
            continue
        
        # Create key based on bucket, user_type and first words
        key_components = [
            chunk.metadata.get("bucket", "misc"),
            chunk.metadata.get("user_type", "general"),
            " ".join(chunk.page_content.split()[:10])  # First 10 words
        ]
        key = "|".join(key_components)
        chunk_groups[key].append(chunk)
    
    deduplicated = []
    
    for group in chunk_groups.values():
        if len(group) == 1:
            deduplicated.extend(group)
        else:
            # Choose the best chunk from the group
            best_chunk = max(group, key=lambda c: (
                priority_map.get(c.metadata.get("status", "purple"), 0),
                c.metadata.get("confidence", 0.0),
                len(c.page_content)
            ))
            best_chunk.metadata["deduplicated"] = True
            deduplicated.append(best_chunk)
    
    logging.info(f"✅ Deduplicated: {len(chunks)} → {len(deduplicated)} chunks")
    return deduplicated

def generate_bucket_report(chunks: List[Document]) -> Dict:
    """
    Generates a detailed report on bucket classification
    """
    report = {
        "total_chunks": len(chunks),
        "bucket_distribution": defaultdict(int),
        "user_type_distribution": defaultdict(int),
        "status_distribution": defaultdict(int),
        "confidence_stats": [],
        "low_confidence_chunks": []
    }
    
    for chunk in chunks:
        bucket = chunk.metadata.get("bucket", "unknown")
        user_type = chunk.metadata.get("user_type", "unknown")
        status = chunk.metadata.get("status", "unknown")
        confidence = chunk.metadata.get("confidence", 0.0)
        
        report["bucket_distribution"][bucket] += 1
        report["user_type_distribution"][user_type] += 1
        report["status_distribution"][status] += 1
        report["confidence_stats"].append(confidence)
        
        if confidence < 0.2:  # Low confidence threshold
            report["low_confidence_chunks"].append({
                "content_preview": chunk.page_content[:100],
                "bucket": bucket,
                "confidence": confidence,
                "source": chunk.metadata.get("source_pdf", "unknown")
            })
    
    return report

# Example of usage
if __name__ == "__main__":
    # Carregar documentos
    folder_path = "data/processed"
    all_docs = load_documents_from_folder(folder_path)
    logging.info(f"📚 Total documents loaded: {len(all_docs)}")
    
    # Preprocessar
    processed_chunks = preprocess_documents(all_docs)
    
    # Deduplicar
    final_chunks = advanced_deduplication(processed_chunks)
    
    # Gerar relatório
    report = generate_bucket_report(final_chunks)
    
    # Salvar relatório
    with open("bucket_classification_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    logging.info("🎯 Bucket classification complete!")
    logging.info(f"📊 Final chunks: {len(final_chunks)}")
    logging.info(f"📋 Report saved to: bucket_classification_report.json")

