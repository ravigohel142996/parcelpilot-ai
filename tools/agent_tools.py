import re
import sqlite3
from datetime import datetime

# Import lower-level implementations from existing packages
from rag.index import search_documents as rag_search
from tools.operational_data import (
    lookup_account as op_lookup_account,
    lookup_order as op_lookup_order,
    lookup_ticket as op_lookup_ticket,
    calculate_service_credit as op_calculate_service_credit,
    get_db_connection,
    SNAPSHOT_TIME_STR
)

def search_documents(query: str) -> list:
    """
    Search the policy documents, SOPs, and product operations guides for answers.
    
    Parameters:
      query (str): The search query text (e.g. "SLA first response targets").
      
    Returns:
      list: A list of relevant passages with authority metadata.
    """
    # 1. Type validation
    if not isinstance(query, str):
        raise TypeError("search_documents parameter 'query' must be a string.")
    
    # 2. Format validation
    query_clean = query.strip()
    if not query_clean:
        raise ValueError("search_documents parameter 'query' cannot be empty or whitespace.")
        
    try:
        # Retrieve relevant passages from the RAG index
        return rag_search(query_clean, top_n=3)
    except Exception as e:
        # Error handling
        return [{"error": f"Failed to execute document search: {e}"}]


def lookup_operational_data(query: str) -> dict:
    """
    Unified keyword search across the structured SQLite database tables (accounts, orders, tickets).
    
    Parameters:
      query (str): Search term (e.g., account name, carrier, assigned agent, or specific IDs).
      
    Returns:
      dict: Matching records grouped by category ('accounts', 'orders', 'tickets').
    """
    # 1. Type validation
    if not isinstance(query, str):
        raise TypeError("lookup_operational_data parameter 'query' must be a string.")
        
    query_clean = query.strip()
    if not query_clean:
        raise ValueError("lookup_operational_data parameter 'query' cannot be empty or whitespace.")
        
    # Check if query matches specific primary key patterns for direct lookups
    # ACCT-###
    if re.match(r'^ACCT-\d+$', query_clean):
        res = op_lookup_account(query_clean)
        return {"accounts": [res] if res else [], "orders": [], "tickets": []}
    # ORD-####
    if re.match(r'^ORD-\d+$', query_clean):
        res = op_lookup_order(query_clean)
        return {"accounts": [], "orders": [res] if res else [], "tickets": []}
    # TKT-###
    if re.match(r'^TKT-\d+$', query_clean):
        res = op_lookup_ticket(query_clean)
        return {"accounts": [], "orders": [], "tickets": [res] if res else []}
        
    # Fallback to wildcard search across relevant columns
    conn = get_db_connection()
    cursor = conn.cursor()
    
    results = {
        "accounts": [],
        "orders": [],
        "tickets": []
    }
    
    like_pattern = f"%{query_clean}%"
    
    try:
        # Search accounts
        cursor.execute("SELECT * FROM accounts WHERE account_name LIKE ?", (like_pattern,))
        results["accounts"] = [dict(row) for row in cursor.fetchall()]
        
        # Search orders
        cursor.execute("SELECT * FROM orders WHERE carrier LIKE ? OR status LIKE ?", (like_pattern, like_pattern))
        results["orders"] = [dict(row) for row in cursor.fetchall()]
        
        # Search tickets
        cursor.execute(
            "SELECT * FROM tickets WHERE subject LIKE ? OR description LIKE ? OR assigned_to LIKE ?", 
            (like_pattern, like_pattern, like_pattern)
        )
        results["tickets"] = [dict(row) for row in cursor.fetchall()]
        
    except sqlite3.Error as e:
        results["error"] = f"Database query failed: {e}"
    finally:
        conn.close()
        
    return results


def propose_escalation(ticket_id: str, priority: str, reason: str) -> dict:
    """
    Propose an escalation for an open support ticket.
    This prepares the escalation details (severity and justification) and saves them for user approval.
    Does NOT modify the database immediately.
    
    Parameters:
      ticket_id (str): Unique ticket ID format TKT-### (e.g. "TKT-501").
      priority (str): Severity rating of the escalation. Must be one of: "P1", "P2", "P3".
      reason (str): Justification for the escalation.
      
    Returns:
      dict: Proposal details outlining the proposed change.
    """
    from agent.approval_state import propose_escalation as state_propose
    try:
        return state_propose(ticket_id, priority, reason)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def create_escalation(ticket_id: str, priority: str, reason: str) -> dict:
    """
    Escalate an open support ticket to the escalation queue.
    Creates an audit log of the escalation and updates the ticket assignment to 'Escalation Team'.
    
    Parameters:
      ticket_id (str): The ticket identifier (e.g. "TKT-501").
      priority (str): Severity rating of the escalation. Must be one of: "P1", "P2", "P3".
      reason (str): Reason for the escalation (e.g. "SLA breach detected" or "manager approval required").
      
    Returns:
      dict: Escalation result summary containing 'escalation_id' and confirmation status.
    """
    # 1. Type validation
    if not isinstance(ticket_id, str):
        raise TypeError("create_escalation parameter 'ticket_id' must be a string.")
    if not isinstance(priority, str):
        raise TypeError("create_escalation parameter 'priority' must be a string.")
    if not isinstance(reason, str):
        raise TypeError("create_escalation parameter 'reason' must be a string.")
        
    # 2. Value validation
    ticket_clean = ticket_id.strip()
    priority_clean = priority.strip().upper()
    reason_clean = reason.strip()
    
    if not ticket_clean or not priority_clean or not reason_clean:
        raise ValueError("All parameters ('ticket_id', 'priority', 'reason') must be non-empty strings.")
        
    if priority_clean not in {"P1", "P2", "P3"}:
        raise ValueError("Invalid priority. Must be one of: 'P1', 'P2', 'P3'.")
        
    # Check format of ticket_id
    if not re.match(r'^TKT-\d+$', ticket_clean):
        raise ValueError("Invalid ticket ID format. Expected TKT-### (e.g. TKT-501).")
        
    # 3. Database operations
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if the ticket exists
        cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_clean,))
        ticket_row = cursor.fetchone()
        if not ticket_row:
            raise ValueError(f"Ticket '{ticket_clean}' does not exist in the database.")
            
        # Access control verification
        from utils.auth import check_account_access
        check_account_access(ticket_row["account_id"])
            
        # Get escalation timestamp (mocked relative to snapshot or current UTC)
        escalation_time = SNAPSHOT_TIME_STR
        
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Insert escalation record
        cursor.execute(
            "INSERT INTO escalations (ticket_id, priority, reason, escalated_at) VALUES (?, ?, ?, ?)",
            (ticket_clean, priority_clean, reason_clean, escalation_time)
        )
        escalation_id = cursor.lastrowid
        
        # Update ticket status to 'escalated' and assign to Escalation Team
        cursor.execute(
            "UPDATE tickets SET status = 'escalated', assigned_to = 'Escalation Team' WHERE ticket_id = ?",
            (ticket_clean,)
        )
        
        conn.commit()
        return {
            "success": True,
            "escalation_id": escalation_id,
            "ticket_id": ticket_clean,
            "assigned_to": "Escalation Team",
            "escalated_at": escalation_time,
            "message": f"Ticket {ticket_clean} successfully escalated (Escalation ID: {escalation_id})."
        }
        
    except Exception as e:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        return {
            "success": False,
            "error": f"Escalation failed: {e}"
        }
    finally:
        conn.close()


def lookup_order(order_id: str) -> dict:
    """
    Look up detailed shipment metadata by order ID.
    
    Parameters:
      order_id (str): Unique order ID format ORD-#### (e.g. "ORD-1001").
      
    Returns:
      dict: Detailed order record containing status, fees, dates, and carrier details.
    """
    try:
        res = op_lookup_order(order_id)
        if res is None:
            return {"error": f"Order '{order_id}' not found."}
        return res
    except Exception as e:
        return {"error": str(e)}


def lookup_account(account_id: str) -> dict:
    """
    Look up registered customer account details by account ID.
    
    Parameters:
      account_id (str): Unique account ID format ACCT-### (e.g. "ACCT-001").
      
    Returns:
      dict: Customer account record containing subscription tier, notes, and CSM details.
    """
    try:
        res = op_lookup_account(account_id)
        if res is None:
            return {"error": f"Account '{account_id}' not found."}
        return res
    except Exception as e:
        return {"error": str(e)}


def lookup_ticket(ticket_id: str) -> dict:
    """
    Look up support ticket details by ticket ID.
    
    Parameters:
      ticket_id (str): Unique ticket ID format TKT-### (e.g. "TKT-501").
      
    Returns:
      dict: Support ticket record containing status, description, and history.
    """
    try:
        res = op_lookup_ticket(ticket_id)
        if res is None:
            return {"error": f"Ticket '{ticket_id}' not found."}
        return res
    except Exception as e:
        return {"error": str(e)}


def calculate_service_credit(order_id: str) -> dict:
    """
    Calculate missed pickup service credit entitlement for a carrier-delayed order.
    
    Parameters:
      order_id (str): Unique order ID format ORD-#### (e.g. "ORD-2002").
      
    Returns:
      dict: Eligibility summary detailing credit amount (INR), rules, and approval flags.
    """
    try:
        return op_calculate_service_credit(order_id)
    except Exception as e:
        return {"error": str(e)}
