import re
import contextvars
import sqlite3
from utils.auth import get_current_user, check_account_access
from tools.operational_data import get_db_connection
from tools.agent_tools import create_escalation

# Thread-safe and session-safe context variable for pending escalations (used in CLI / Pytest)
_pending_escalation = contextvars.ContextVar("pending_escalation", default=None)

def _get_storage():
    """
    Retrieves the persistent storage container.
    Returns Streamlit's session_state if running in Streamlit, otherwise returns None.
    """
    try:
        import streamlit as st
        # st.runtime.exists() is True if the Streamlit server is active
        if st.runtime.exists():
            return st.session_state
    except ImportError:
        pass
    return None

def propose_escalation(ticket_id: str, priority: str, reason: str) -> dict:
    """
    Proposes an escalation for a ticket, validating fields and permissions.
    Stores the proposal in the pending context without executing the change.
    """
    # 1. Type validation
    if not isinstance(ticket_id, str):
        raise TypeError("propose_escalation parameter 'ticket_id' must be a string.")
    if not isinstance(priority, str):
        raise TypeError("propose_escalation parameter 'priority' must be a string.")
    if not isinstance(reason, str):
        raise TypeError("propose_escalation parameter 'reason' must be a string.")
        
    # 2. Value validation
    ticket_clean = ticket_id.strip()
    priority_clean = priority.strip().upper()
    reason_clean = reason.strip()
    
    if not ticket_clean or not priority_clean or not reason_clean:
        raise ValueError("All parameters ('ticket_id', 'priority', 'reason') must be non-empty strings.")
        
    if priority_clean not in {"P1", "P2", "P3"}:
        raise ValueError("Invalid priority. Must be one of: 'P1', 'P2', 'P3'.")
        
    if not re.match(r'^TKT-\d+$', ticket_clean):
        raise ValueError("Invalid ticket ID format. Expected TKT-### (e.g. TKT-501).")

    # 3. Check database record existence and authorization
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_id FROM tickets WHERE ticket_id = ?", (ticket_clean,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise ValueError(f"Ticket '{ticket_clean}' does not exist in the database.")
        
    # Verify account access (raises PermissionError if unauthorized)
    check_account_access(row["account_id"])

    # 4. Save proposal to state
    proposal = {
        "ticket_id": ticket_clean,
        "priority": priority_clean,
        "reason": reason_clean
    }
    
    storage = _get_storage()
    if storage is not None:
        storage["pending_escalation"] = proposal
    else:
        _pending_escalation.set(proposal)
    
    return {
        "proposed": True,
        "ticket_id": ticket_clean,
        "priority": priority_clean,
        "reason": reason_clean,
        "action": "Create Escalation in Database",
        "message": f"Proposal prepared: High-priority escalation for {ticket_clean} ({priority_clean}) because: {reason_clean}. Waiting for user confirmation."
    }

def confirm_escalation() -> dict:
    """
    Confirms and executes the pending escalation.
    Clears the pending state.
    """
    storage = _get_storage()
    if storage is not None:
        proposal = storage.get("pending_escalation")
    else:
        proposal = _pending_escalation.get()
        
    if not proposal:
        raise ValueError("No pending escalation found to confirm.")
        
    # Call the actual state-changing tool
    result = create_escalation(
        ticket_id=proposal["ticket_id"],
        priority=proposal["priority"],
        reason=proposal["reason"]
    )
    
    # Clear the pending state
    if storage is not None:
        storage["pending_escalation"] = None
    else:
        _pending_escalation.set(None)
    
    return result

def cancel_escalation() -> dict:
    """
    Cancels the pending escalation and clears the pending state.
    """
    storage = _get_storage()
    if storage is not None:
        proposal = storage.get("pending_escalation")
        storage["pending_escalation"] = None
    else:
        proposal = _pending_escalation.get()
        _pending_escalation.set(None)
    
    if not proposal:
        return {
            "success": True,
            "message": "No pending escalation existed. State is clean."
        }
        
    return {
        "success": True,
        "message": f"Pending escalation for ticket {proposal['ticket_id']} has been cancelled. No action was executed."
    }

def get_pending_escalation() -> dict:
    """
    Returns the current pending escalation proposal, or None.
    """
    storage = _get_storage()
    if storage is not None:
        # st.get can return None, but let's make sure we handle if key doesn't exist
        return storage.get("pending_escalation")
    return _pending_escalation.get()
