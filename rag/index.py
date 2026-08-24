import os
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag.loader import load_all_documents
from rag.chunker import chunk_all_documents

# Path for the serialized local index
INDEX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "db",
    "vector_index.pkl"
)

# Global variables for caching loaded index
_VECTORIZER = None
_TFIDF_MATRIX = None
_CHUNKS = None

def build_index(raw_data_dir: str, save_path: str = INDEX_PATH):
    """
    Loads all documents, chunks them, fits TF-IDF, vectorizes chunks, and saves to disk.
    """
    print(f"Building document index from {raw_data_dir}...")
    documents = load_all_documents(raw_data_dir)
    chunks = chunk_all_documents(documents)
    
    if not chunks:
        raise ValueError("No text chunks extracted from documents. Index cannot be built.")
        
    chunk_texts = [chunk["text"] for chunk in chunks]
    
    # Initialize and fit TF-IDF vectorizer
    # We use sublinear_tf=True and lowercasing to handle query terms gracefully
    vectorizer = TfidfVectorizer(
        sublinear_tf=True,
        lowercase=True,
        stop_words="english"
    )
    tfidf_matrix = vectorizer.fit_transform(chunk_texts)
    
    # Save elements to file
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        pickle.dump({
            "vectorizer": vectorizer,
            "tfidf_matrix": tfidf_matrix,
            "chunks": chunks
        }, f)
        
    print(f"Index built successfully and saved to {save_path} with {len(chunks)} chunks.")
    
    # Cache in memory
    global _VECTORIZER, _TFIDF_MATRIX, _CHUNKS
    _VECTORIZER = vectorizer
    _TFIDF_MATRIX = tfidf_matrix
    _CHUNKS = chunks

def load_index(save_path: str = INDEX_PATH):
    """Loads the index from save_path into memory cache."""
    global _VECTORIZER, _TFIDF_MATRIX, _CHUNKS
    
    if not os.path.exists(save_path):
        # Auto-build index if data/raw/ is available
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        raw_data_dir = os.path.join(base_dir, "data", "raw")
        if os.path.exists(raw_data_dir) and any(f.endswith(".pdf") for f in os.listdir(raw_data_dir)):
            build_index(raw_data_dir, save_path)
        else:
            raise FileNotFoundError(f"Index file {save_path} not found and raw PDFs not available to auto-build.")
            
    with open(save_path, "rb") as f:
        data = pickle.load(f)
        _VECTORIZER = data["vectorizer"]
        _TFIDF_MATRIX = data["tfidf_matrix"]
        _CHUNKS = data["chunks"]

def search_documents(query: str, top_n: int = 3) -> list:
    """
    Searches the indexed chunks for the query using cosine similarity over TF-IDF vectors.
    
    Returns a list of dicts, each containing:
      - "text": The passage text
      - "raw_text": The passage raw text
      - "source": The source filename
      - "metadata": Full metadata dictionary (precedence, status, account_id, type, title, etc.)
      - "relevance_score": Cosine similarity score (float)
    """
    global _VECTORIZER, _TFIDF_MATRIX, _CHUNKS
    
    # Ensure index is loaded
    if _VECTORIZER is None or _TFIDF_MATRIX is None or _CHUNKS is None:
        load_index()
        
    # Vectorize query
    query_vector = _VECTORIZER.transform([query])
    
    # Calculate cosine similarities
    similarities = cosine_similarity(query_vector, _TFIDF_MATRIX).flatten()
    
    # Get top-N indices
    top_indices = np.argsort(similarities)[::-1][:top_n]
    
    results = []
    for idx in top_indices:
        score = float(similarities[idx])
        # Only return results with non-zero similarity to avoid unrelated matches
        if score <= 0.0:
            continue
            
        chunk = _CHUNKS[idx]
        results.append({
            "text": chunk["text"],
            "raw_text": chunk["raw_text"],
            "source": chunk["metadata"]["filename"],
            "metadata": chunk["metadata"],
            "relevance_score": score
        })
        
    return results
