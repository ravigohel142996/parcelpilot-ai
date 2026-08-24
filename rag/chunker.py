import re

def clean_text(text: str) -> str:
    """Basic text cleanup."""
    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Standardize line endings
    text = text.replace('\r\n', '\n')
    return text.strip()

def chunk_document(document: dict, min_chunk_size: int = 50) -> list:
    """
    Intelligently splits a document into chunks.
    Uses paragraph boundaries (\n\n) or section headers to split.
    Each chunk retains a copy of the parent document metadata and includes context prefixing.
    """
    text = clean_text(document["text"])
    metadata = document["metadata"]
    
    # Split text into paragraphs
    paragraphs = text.split("\n\n")
    
    chunks = []
    current_section = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # Check if this paragraph looks like a section header (e.g., "1. Support terms", "KI-208 - ...")
        # If it does, we record it to prefix subsequent paragraphs in the same document.
        header_match = re.match(r'^(\d+\.\s+[A-Za-z0-9\-\s\(\)&]+|KI-\d+\s+-\s+[A-Za-z0-9\-\s\(\)&:]+)', para)
        if header_match:
            current_section = header_match.group(1).strip()
            
        # Skip extremely short chunks that don't contain meaningful text
        if len(para) < min_chunk_size and not header_match:
            continue
            
        # Create a text representation that includes document-level and section-level context
        context_prefix = f"[{metadata['title']}]"
        if current_section and current_section not in para:
            context_prefix += f" {current_section}:"
            
        chunk_text = f"{context_prefix} {para}"
        
        # Clone metadata and append to chunk info
        chunk_metadata = metadata.copy()
        chunk_metadata["section"] = current_section
        
        chunks.append({
            "text": chunk_text,
            "raw_text": para,
            "metadata": chunk_metadata
        })
        
    return chunks

def chunk_all_documents(documents: list) -> list:
    """Chunks all documents in the provided list."""
    all_chunks = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))
    return all_chunks
