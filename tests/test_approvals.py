import pytest
import sqlite3
from contextlib import closing
from utils.auth import UserContext, active_user
from tools.operational_data import get_db_connection
from agent.approval_state import (
    propose_escalation,
    confirm_escalation,
    cancel_escalation,
    get_pending_escalation
)

def test_no_execution_before_confirmation():
    """Verify that proposing an escalation updates the pending state but does not change database state."""
    ticket_id = "TKT-502"
    
    # 1. Verify initial status in database
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, assigned_to FROM tickets WHERE ticket_id = ?", (ticket_id,))
        row = cursor.fetchone()
        assert row["status"] == "open"
        assert row["assigned_to"] == "Maya"
        
        # Ensure pending state is initially empty
        assert get_pending_escalation() is None
        
        # 2. Propose escalation
        res = propose_escalation(ticket_id, "P2", "SLA at risk")
        assert res["proposed"] is True
        assert res["ticket_id"] == ticket_id
        
        # 3. Verify pending state is populated
        pending = get_pending_escalation()
        assert pending is not None
        assert pending["ticket_id"] == ticket_id
        assert pending["priority"] == "P2"
        assert pending["reason"] == "SLA at risk"
        
        # 4. Verify database state remains unchanged
        cursor.execute("SELECT status, assigned_to FROM tickets WHERE ticket_id = ?", (ticket_id,))
        row_check = cursor.fetchone()
        assert row_check["status"] == "open"
        assert row_check["assigned_to"] == "Maya"
        
        # Verify no escalation record was inserted
        cursor.execute("SELECT * FROM escalations WHERE ticket_id = ?", (ticket_id,))
        assert cursor.fetchone() is None

def test_execution_after_confirmation():
    """Verify that confirming a proposed escalation executes the database change and clears pending state."""
    ticket_id = "TKT-502"
    
    # Propose escalation
    propose_escalation(ticket_id, "P2", "SLA at risk")
    assert get_pending_escalation() is not None
    
    # Confirm escalation
    confirm_res = confirm_escalation()
    assert confirm_res["success"] is True
    assert confirm_res["assigned_to"] == "Escalation Team"
    
    # 1. Verify pending state is cleared
    assert get_pending_escalation() is None
    
    # 2. Verify database state has changed
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, assigned_to FROM tickets WHERE ticket_id = ?", (ticket_id,))
        row = cursor.fetchone()
        assert row["status"] == "escalated"
        assert row["assigned_to"] == "Escalation Team"
        
        # Verify escalation record exists
        cursor.execute("SELECT * FROM escalations WHERE ticket_id = ?", (ticket_id,))
        esc_record = cursor.fetchone()
        assert esc_record is not None
        assert esc_record["priority"] == "P2"
        assert esc_record["reason"] == "SLA at risk"

def test_cancellation_leaves_state_unchanged():
    """Verify that cancelling a proposed escalation clears pending state and leaves DB unchanged."""
    ticket_id = "TKT-502"
    
    # Propose escalation
    propose_escalation(ticket_id, "P2", "SLA at risk")
    assert get_pending_escalation() is not None
    
    # Cancel escalation
    cancel_res = cancel_escalation()
    assert cancel_res["success"] is True
    assert "cancelled" in cancel_res["message"]
    
    # 1. Verify pending state is cleared
    assert get_pending_escalation() is None
    
    # 2. Verify database remains unchanged (status is still 'open')
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, assigned_to FROM tickets WHERE ticket_id = ?", (ticket_id,))
        row = cursor.fetchone()
        assert row["status"] == "open"
        assert row["assigned_to"] == "Maya"

def test_confirm_without_proposal_raises_error():
    """Verify that confirming when no proposal is active raises an error."""
    # Clean pending state
    cancel_escalation()
    assert get_pending_escalation() is None
    
    with pytest.raises(ValueError) as excinfo:
        confirm_escalation()
    assert "No pending escalation" in str(excinfo.value)

def test_propose_escalation_security():
    """Verify that propose_escalation respects user account access constraints."""
    # Create restricted user for ACCT-001
    northstar_user = UserContext("contact-northstar", "CUSTOMER_SUPPORT", ["ACCT-001"])
    
    with active_user(northstar_user):
        # TKT-502 is for ACCT-002 (LumenWorks) - Access should raise PermissionError
        with pytest.raises(PermissionError):
            propose_escalation("TKT-502", "P2", "SLA breach")
            
        # TKT-501 is for ACCT-001 (Northstar) - Should succeed
        res = propose_escalation("TKT-501", "P1", "Outage")
        assert res["proposed"] is True
