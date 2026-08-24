import pytest
from agent.agent import run_agent_query

def test_trust_northstar_conflict_resolution():
    """Verify that query for Northstar cancellation fees detects conflict and ranks contract highest."""
    query = "Can Northstar cancel ORD-1001 without a cancellation fee? Explain why."
    
    res = run_agent_query(query)
    
    # 1. Assert correct trust metadata fields are present
    assert res["confidence"] == "HIGH"
    assert res["conflict_detected"] is True
    assert "05_Northstar_Logistics_Enterprise_Agreement.pdf" in res["authoritative_source"]
    assert "SOP" in res["conflict_details"]
    assert "Agreement" in res["conflict_details"]

def test_trust_lumenworks_precedence():
    """Verify that query for delay credit compares custom agreements with standard SOP."""
    query = "A pickup is three hours late because of carrier fault. Should I get a service credit? Explain if this applies to all accounts."
    
    res = run_agent_query(query)
    
    # 2. Assert correct trust override calculations
    assert res["confidence"] == "HIGH"
    assert res["conflict_detected"] is True
    assert "LumenWorks" in res["authoritative_source"]
    assert "SOP" in res["authoritative_source"]
    assert "LumenWorks" in res["conflict_details"]

def test_trust_low_confidence_insufficient_evidence():
    """Verify that unknown/contradictory queries flag LOW confidence and recommend escalation."""
    query = "Review the contradictory and insufficient policies for an unknown order on an unresolvable account."
    
    res = run_agent_query(query)
    
    # 3. Assert low confidence output
    assert res["confidence"] == "LOW"
    assert res["conflict_detected"] is True
    assert "insufficient" in res["answer"].lower() or "unable" in res["answer"].lower()
    assert "escalat" in res["answer"].lower() or "human" in res["answer"].lower()
    assert "None" in res["authoritative_source"] or "Insufficient" in res["authoritative_source"]
