import os
import sqlite3
from datetime import datetime

from utils.auth import check_account_access, get_current_user


# Path to database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "parcelpilot.db")

# Whitelist definition to prevent SQL injection or schema enumeration
WHITELIST_TABLES = {
    "accounts": {
        "columns": {"account_id", "account_name", "plan", "status", "csm", "contract_file", "premium_support", "notes"},
        "id_col": "account_id"
    },
    "orders": {
        "columns": {"order_id", "account_id", "carrier", "status", "booked_at", "pickup_window_start", 
                    "pickup_window_end", "pickup_actual_at", "shipment_fee_inr", "carrier_fault", 
                    "customer_fault", "cancellation_requested_at", "notes"},
        "id_col": "order_id"
    },
    "tickets": {
        "columns": {"ticket_id", "account_id", "created_at", "status", "subject", "description", 
                    "channel", "assigned_to", "last_customer_message_at", "historical_resolution"},
        "id_col": "ticket_id"
    }
}

# Reference snapshot time from README sheet
SNAPSHOT_TIME_STR = "2026-08-16 11:00"
SNAPSHOT_TIME = datetime.strptime(SNAPSHOT_TIME_STR, "%Y-%m-%d %H:%M")

def get_db_connection():
    """Establishes and returns a database connection that returns rows as dictionaries."""
    if not os.path.exists(DB_PATH):
        from db.setup_db import setup_database
        setup_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def lookup_account(account_id: str) -> dict:
    """
    Looks up details for a specific account.
    Returns account dict, or None if not found.
    Validates input format.
    """
    if not account_id or not isinstance(account_id, str):
        raise ValueError("Invalid account_id format. Must be a non-empty string.")
    
    # ID validation pattern: ACCT-###
    if not account_id.startswith("ACCT-") or not account_id[5:].isdigit():
        raise ValueError("Invalid account ID format. Expected ACCT-### (e.g. ACCT-001).")

    # Access control verification
    check_account_access(account_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def lookup_order(order_id: str) -> dict:
    """
    Looks up details for a specific order.
    Returns order dict, or None if not found.
    Validates input format.
    """
    if not order_id or not isinstance(order_id, str):
        raise ValueError("Invalid order_id format. Must be a non-empty string.")
        
    # ID validation pattern: ORD-####
    if not order_id.startswith("ORD-") or not order_id[4:].isdigit():
        raise ValueError("Invalid order ID format. Expected ORD-#### (e.g. ORD-1001).")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        order = dict(row)
        # Access control verification
        check_account_access(order["account_id"])
        return order
    return None

def lookup_ticket(ticket_id: str) -> dict:
    """
    Looks up details for a specific support ticket.
    Returns ticket dict, or None if not found.
    Validates input format.
    """
    if not ticket_id or not isinstance(ticket_id, str):
        raise ValueError("Invalid ticket_id format. Must be a non-empty string.")
        
    # ID validation pattern: TKT-###
    if not ticket_id.startswith("TKT-") or not ticket_id[4:].isdigit():
        raise ValueError("Invalid ticket ID format. Expected TKT-### (e.g. TKT-501).")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        ticket = dict(row)
        # Access control verification
        check_account_access(ticket["account_id"])
        return ticket
    return None

def query_operational_data(table_name: str, filters: dict = None) -> list:
    """
    Safely queries rows from a whitelisted table with dynamic filters.
    Constructs parameterized SQL queries to prevent injection.
    
    table_name: must be one of 'accounts', 'orders', 'tickets'
    filters: dict of col_name: value pairs
    """
    if table_name not in WHITELIST_TABLES:
        raise ValueError(f"Unauthorized table name '{table_name}'. Query restricted to whitelisted tables.")
        
    # Get current active user (raises PermissionError if no context is active)
    user = get_current_user()
    
    table_config = WHITELIST_TABLES[table_name]
    
    query = f"SELECT * FROM {table_name}"
    params = []
    
    if filters:
        filter_clauses = []
        for col, val in filters.items():
            if col not in table_config["columns"]:
                raise ValueError(f"Unauthorized column filter '{col}' for table '{table_name}'.")
            filter_clauses.append(f"{col} = ?")
            params.append(val)
        
        if filter_clauses:
            query += " WHERE " + " AND ".join(filter_clauses)
            
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Filter rows based on access context
    filtered_results = []
    for row in rows:
        row_dict = dict(row)
        rec_account = row_dict.get("account_id")
        
        # In the 'accounts' table, the primary key itself is 'account_id'
        if table_name == "accounts":
            rec_account = row_dict.get("account_id")
            
        # Wildcard access or explicit account match check
        if "*" in user.authorised_accounts or rec_account in user.authorised_accounts:
            filtered_results.append(row_dict)
            
    return filtered_results

def calculate_service_credit(order_id: str) -> dict:
    """
    Calculates the eligible service credit for a missed carrier pickup.
    Applies custom overrides from signed client agreements if applicable.
    
    Returns a dictionary indicating eligibility, credit amount in INR, and rule details.
    """
    order = lookup_order(order_id)
    if not order:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "reason": "Order not found",
            "requires_manager_approval": False
        }
        
    account_id = order["account_id"]
    account = lookup_account(account_id)
    if not account:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "reason": "Account associated with order not found",
            "requires_manager_approval": False
        }
        
    # Check carrier/customer fault parameters
    carrier_fault = bool(order["carrier_fault"])
    customer_fault = bool(order["customer_fault"])
    
    if not carrier_fault:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "reason": "Carrier is not at fault for delay",
            "requires_manager_approval": False
        }
        
    if customer_fault:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "reason": "Customer contributed to delay / was at fault",
            "requires_manager_approval": False
        }
        
    # Determine actual pickup time, or fall back to snapshot time if still BOOKED
    pickup_window_end_str = order["pickup_window_end"]
    pickup_actual_at_str = order["pickup_actual_at"]
    
    if not pickup_window_end_str:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "reason": "No pickup window defined for order",
            "requires_manager_approval": False
        }
        
    try:
        window_end_dt = datetime.strptime(pickup_window_end_str, "%Y-%m-%d %H:%M")
        
        if pickup_actual_at_str:
            actual_pickup_dt = datetime.strptime(pickup_actual_at_str, "%Y-%m-%d %H:%M")
        else:
            # Missed pickup, not yet collected at the time of the snapshot
            actual_pickup_dt = SNAPSHOT_TIME
            
    except ValueError as e:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "reason": f"Error parsing datetime fields: {e}",
            "requires_manager_approval": False
        }
        
    # Calculate delay in hours
    delay_delta = actual_pickup_dt - window_end_dt
    delay_hours = delay_delta.total_seconds() / 3600.0
    
    if delay_hours <= 0:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "delay_hours": delay_hours,
            "reason": f"Pickup was completed within schedule (delay hours: {delay_hours:.2f})",
            "requires_manager_approval": False
        }
        
    # Apply rules based on account terms
    shipment_fee = float(order["shipment_fee_inr"] or 0.0)
    credit_amount = 0.0
    rule_applied = ""
    
    # ACCT-002: LumenWorks Service Agreement
    # "If a pickup is more than 4 hours past the end of the scheduled pickup window...
    # LumenWorks receives a fixed INR 300 service credit. Replaces default SOP."
    if account_id == "ACCT-002":
        threshold_hours = 4.0
        if delay_hours > threshold_hours:
            credit_amount = 300.0
            eligible = True
            rule_applied = "LumenWorks Contract - Fixed INR 300 for delay > 4 hours"
        else:
            eligible = False
            rule_applied = "LumenWorks Contract - Missed 4-hour delay threshold"
            
    # ACCT-001 (Northstar) & Others: Default SOP v4
    # "pickup is more than 2 hours past the end... lower of INR 500 or 10% of shipment fee"
    else:
        threshold_hours = 2.0
        if delay_hours > threshold_hours:
            credit_amount = min(500.0, 0.10 * shipment_fee)
            eligible = True
            rule_applied = f"Default SOP v4 - Lower of INR 500 or 10% of fee (Shipment Fee: INR {shipment_fee})"
        else:
            eligible = False
            rule_applied = "Default SOP v4 - Missed 2-hour delay threshold"
            
    if not eligible:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "delay_hours": delay_hours,
            "reason": f"Delay of {delay_hours:.2f} hours did not exceed the required threshold of {threshold_hours} hours.",
            "rule_applied": rule_applied,
            "requires_manager_approval": False
        }
        
    # Rule 3 of SOP: Credit > 1,000 requires manager approval. (For default it is max 500, but custom contracts might exceed)
    requires_approval = credit_amount > 1000.0
    
    return {
        "eligible": True,
        "credit_amount": credit_amount,
        "delay_hours": delay_hours,
        "rule_applied": rule_applied,
        "requires_manager_approval": requires_approval
    }
