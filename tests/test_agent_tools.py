import pytest
import sqlite3
from tools.agent_tools import (
    search_documents,
    lookup_operational_data,
    create_escalation,
    lookup_order,
    lookup_account,
    lookup_ticket,
    calculate_service_credit
)
from tools.operational_data import get_db_connection

def test_agent_search_documents():
    """Verify search_documents tool validation and output."""
    # Test valid query
    results = search_documents("cancellation fee")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "source" in results[0]
    
    # Test empty query error handling
    with pytest.raises(ValueError):
        search_documents("")
        
    with pytest.raises(ValueError):
        search_documents("   ")
        
    # Test invalid parameter type
    with pytest.raises(TypeError):
        search_documents(12345)

def test_agent_lookup_operational_data():
    """Verify lookup_operational_data unified search functionality."""
    # 1. Test query by exact ID
    res_acct = lookup_operational_data("ACCT-001")
    assert len(res_acct["accounts"]) == 1
    assert res_acct["accounts"][0]["account_name"] == "Northstar Logistics"
    
    res_order = lookup_operational_data("ORD-1001")
    assert len(res_order["orders"]) == 1
    assert res_order["orders"][0]["order_id"] == "ORD-1001"
    
    res_ticket = lookup_operational_data("TKT-501")
    assert len(res_ticket["tickets"]) == 1
    assert res_ticket["tickets"][0]["ticket_id"] == "TKT-501"

    # 2. Test query by wildcard string
    # Searching "Northstar" should match the account
    res_wildcard_acct = lookup_operational_data("Northstar")
    assert len(res_wildcard_acct["accounts"]) == 1
    assert res_wildcard_acct["accounts"][0]["account_name"] == "Northstar Logistics"
    
    # Searching "failing" should match the ticket TKT-501
    res_wildcard_ticket = lookup_operational_data("failing")
    assert len(res_wildcard_ticket["tickets"]) >= 1
    assert any(t["ticket_id"] == "TKT-501" for t in res_wildcard_ticket["tickets"])
    
    # Searching a carrier like "SwiftShip" should match orders
    res_wildcard_carrier = lookup_operational_data("SwiftShip")
    assert len(res_wildcard_carrier["orders"]) > 0
    assert any(o["order_id"] == "ORD-1001" for o in res_wildcard_carrier["orders"])

    # 3. Test validation errors
    with pytest.raises(ValueError):
        lookup_operational_data("")
    with pytest.raises(TypeError):
        lookup_operational_data(None)

def test_agent_create_escalation():
    """Verify create_escalation functionality, ticket status changes, and input validation."""
    # We will test escalation on TKT-503 (or TKT-502) to verify it inserts and updates correctly
    ticket_id = "TKT-503"
    
    # Check ticket state before escalation
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, assigned_to FROM tickets WHERE ticket_id = ?", (ticket_id,))
    before_row = cursor.fetchone()
    assert before_row["status"] == "open"
    assert before_row["assigned_to"] == "Rohit"
    
    # Perform escalation
    priority = "P1"
    reason = "Test escalation reason"
    res = create_escalation(ticket_id, priority, reason)
    
    assert res["success"] is True
    assert res["assigned_to"] == "Escalation Team"
    assert "escalation_id" in res
    
    # Verify state in database after escalation
    cursor.execute("SELECT status, assigned_to FROM tickets WHERE ticket_id = ?", (ticket_id,))
    after_row = cursor.fetchone()
    assert after_row["status"] == "escalated"
    assert after_row["assigned_to"] == "Escalation Team"
    
    # Verify escalation audit record exists
    cursor.execute("SELECT * FROM escalations WHERE ticket_id = ?", (ticket_id,))
    escalation_row = cursor.fetchone()
    assert escalation_row is not None
    assert escalation_row["priority"] == "P1"
    assert escalation_row["reason"] == "Test escalation reason"
    
    conn.close()

def test_agent_create_escalation_validation():
    """Verify input validation constraints on create_escalation."""
    # 1. Non-existent ticket (checked at DB runtime, returns success=False dict)
    res = create_escalation("TKT-999", "P1", "Reason")
    assert res["success"] is False
    assert "does not exist" in res["error"]
    
    # 2. Malformed ticket ID format
    with pytest.raises(ValueError):
        create_escalation("TKT-abc", "P1", "Reason")
        
    # 3. Invalid priority value
    with pytest.raises(ValueError) as excinfo:
        create_escalation("TKT-501", "URGENT", "Reason")
    assert "Invalid priority" in str(excinfo.value)
    
    # 4. Empty fields
    with pytest.raises(ValueError):
        create_escalation("TKT-501", "P1", "")
    with pytest.raises(ValueError):
        create_escalation("", "P1", "Reason")
        
    # 5. Type validation
    with pytest.raises(TypeError):
        create_escalation("TKT-501", 1, "Reason")

def test_agent_lookup_wrappers():
    """Verify basic lookups and calculation wrappers function correctly and return error dicts when missing."""
    # Valid lookups
    assert "error" not in lookup_account("ACCT-001")
    assert "error" not in lookup_order("ORD-1001")
    assert "error" not in lookup_ticket("TKT-501")
    assert "eligible" in calculate_service_credit("ORD-2002")
    
    # Missing records error dictionary outputs
    assert "error" in lookup_account("ACCT-999")
    assert "error" in lookup_order("ORD-9999")
    assert "error" in lookup_ticket("TKT-999")
