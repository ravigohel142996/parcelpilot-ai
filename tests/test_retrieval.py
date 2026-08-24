import os
import pytest
from rag.loader import load_all_documents
from rag.chunker import chunk_all_documents, chunk_document
from rag.index import build_index, load_index, search_documents, INDEX_PATH

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

def test_loader():
    """Verify that documents can be loaded and have required metadata tags."""
    documents = load_all_documents(RAW_DATA_DIR)
    assert len(documents) > 0, "No documents were loaded"
    
    # Check that each document has correct keys in metadata
    for doc in documents:
        assert "text" in doc
        metadata = doc["metadata"]
        assert "filename" in metadata
        assert "title" in metadata
        assert "document_type" in metadata
        assert "version" in metadata
        assert "status" in metadata
        assert "authority" in metadata
        assert "precedence" in metadata
        assert "account_id" in metadata

def test_chunker():
    """Verify chunking behavior and metadata propagation."""
    documents = load_all_documents(RAW_DATA_DIR)
    sample_doc = documents[0]
    
    chunks = chunk_document(sample_doc)
    assert len(chunks) > 0, "No chunks were generated for document"
    
    # Check that chunks retain metadata and have context prefixing
    for chunk in chunks:
        assert "text" in chunk
        assert "raw_text" in chunk
        assert "metadata" in chunk
        
        # Metadata values should match parent document
        assert chunk["metadata"]["filename"] == sample_doc["metadata"]["filename"]
        # Prefix context check
        assert sample_doc["metadata"]["title"] in chunk["text"]

def test_index_build_and_search():
    """Verify index building, loading, and document search retrieval."""
    # Ensure raw directory has documents
    assert os.path.exists(RAW_DATA_DIR), f"Raw directory {RAW_DATA_DIR} does not exist"
    
    # 1. Build index
    build_index(RAW_DATA_DIR, INDEX_PATH)
    assert os.path.exists(INDEX_PATH), f"Vector index file {INDEX_PATH} was not created"
    
    # 2. Load index
    load_index(INDEX_PATH)
    
    # 3. Test generic support policy search
    results_sla = search_documents("P1 response targets", top_n=3)
    assert len(results_sla) > 0, "Search for 'P1 response targets' returned no results"
    # The top results should contain Support Policy information
    top_result = results_sla[0]
    assert "SLA" in top_result["text"] or "SLA" in top_result["metadata"]["title"] or "Support Policy" in top_result["metadata"]["title"] or "Agreement" in top_result["metadata"]["title"]
    assert top_result["relevance_score"] > 0.0
    
    # 4. Test customer-specific query: Northstar Logistics
    results_northstar = search_documents("Northstar support response targets", top_n=2)
    assert len(results_northstar) > 0
    # Should find the Northstar Logistics Enterprise Agreement
    has_northstar_doc = any("Northstar" in r["metadata"]["title"] or r["metadata"]["account_id"] == "ACCT-001" for r in results_northstar)
    assert has_northstar_doc, "Search for Northstar support targets failed to retrieve Northstar agreement"
    
    # 5. Test cancellation query
    results_cancel = search_documents("cancellation fee BOOKED shipment", top_n=3)
    assert len(results_cancel) > 0
    # Should retrieve Cancellation SOP v4 or Northstar contract
    has_cancel_policy = any("Cancellation" in r["metadata"]["title"] or "Agreement" in r["metadata"]["title"] for r in results_cancel)
    assert has_cancel_policy, "Search for cancellation terms failed to retrieve relevant policies"
    
    # 6. Verify structure of search response
    first_res = results_cancel[0]
    assert "text" in first_res
    assert "raw_text" in first_res
    assert "source" in first_res
    assert "metadata" in first_res
    assert "relevance_score" in first_res
    assert isinstance(first_res["relevance_score"], float)
    
    # Check that metadata contains precedence and authority for conflict resolution
    assert "precedence" in first_res["metadata"]
    assert "authority" in first_res["metadata"]
