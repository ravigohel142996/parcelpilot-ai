import os
from pypdf import PdfReader

# Document metadata registry based on exact filenames in data/raw/
DOCUMENT_REGISTRY = {
    "01_Support_Policy_v3_CURRENT.pdf": {
        "title": "ParcelPilot Support Policy v3",
        "document_type": "Support Policy",
        "version": "v3",
        "status": "CURRENT",
        "authority": "Default Support Policy (Standard default)",
        "precedence": 2,
        "account_id": None
    },
    "02_Support_Policy_v2_DEPRECATED.pdf": {
        "title": "ParcelPilot Support Policy v2",
        "document_type": "Support Policy",
        "version": "v2",
        "status": "DEPRECATED",
        "authority": "Deprecated Support Policy (Historical reference only)",
        "precedence": 0,
        "account_id": None
    },
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf": {
        "title": "ParcelPilot Cancellation & Service Credit SOP v4",
        "document_type": "SOP",
        "version": "v4",
        "status": "CURRENT",
        "authority": "Default Cancellation & Service Credit SOP",
        "precedence": 3,
        "account_id": None
    },
    "04_Product_Operations_Guide_and_Known_Issues.pdf": {
        "title": "ParcelPilot Product Operations Guide",
        "document_type": "Operations Guide",
        "version": "v1 (Updated 14 August 2026)",
        "status": "CURRENT",
        "authority": "Product Operations Guide (Product truth / known issues)",
        "precedence": 3,
        "account_id": None
    },
    "05_Northstar_Logistics_Enterprise_Agreement.pdf": {
        "title": "ParcelPilot - Northstar Logistics Enterprise Agreement",
        "document_type": "Customer Agreement",
        "version": "v1",
        "status": "ACTIVE",
        "authority": "Northstar Logistics Custom Contract",
        "precedence": 1,
        "account_id": "ACCT-001"
    },
    "06_LumenWorks_Service_Agreement.pdf": {
        "title": "ParcelPilot - LumenWorks Service Agreement",
        "document_type": "Customer Agreement",
        "version": "v1",
        "status": "ACTIVE",
        "authority": "LumenWorks Custom Contract",
        "precedence": 1,
        "account_id": "ACCT-002"
    }
}

def load_pdf_text(filepath: str) -> str:
    """Extracts all text from a given PDF file path."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"PDF file not found at {filepath}")
    
    reader = PdfReader(filepath)
    text_content = []
    for page_idx, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            text_content.append(page_text)
    return "\n".join(text_content)

def load_all_documents(raw_data_dir: str):
    """Loads all PDF files in raw_data_dir and maps them to their registry metadata."""
    documents = []
    
    if not os.path.exists(raw_data_dir):
        raise FileNotFoundError(f"Raw data directory not found at {raw_data_dir}")
        
    for filename in os.listdir(raw_data_dir):
        if not filename.endswith(".pdf"):
            continue
            
        filepath = os.path.join(raw_data_dir, filename)
        
        # Extract text content
        try:
            text = load_pdf_text(filepath)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
            
        # Get metadata from registry, or use defaults for unregistered documents
        metadata = DOCUMENT_REGISTRY.get(filename, {
            "title": os.path.splitext(filename)[0],
            "document_type": "Unknown",
            "version": "Unknown",
            "status": "Unknown",
            "authority": "Unverified document",
            "precedence": 4,
            "account_id": None
        }).copy()
        
        metadata["filename"] = filename
        
        documents.append({
            "text": text,
            "metadata": metadata
        })
        
    return documents
