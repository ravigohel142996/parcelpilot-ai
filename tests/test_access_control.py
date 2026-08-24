import pytest
from utils.auth import UserContext, active_user

# Import high-level agent tools
from tools.agent_tools import (
    lookup_account,
    lookup_order,
    lookup_ticket,
    calculate_service_credit,
    create_escalation
)

# Import low-level data tools to verify exception raising
from tools.operational_data import (
    lookup_account as op_lookup_account,
    lookup_order as op_lookup_order,
    lookup_ticket as op_lookup_ticket,
    calculate_service_credit as op_calculate_service_credit,
    query_operational_data
)

def test_authorized_access():
    """Verify that a user with restricted permissions can access authorized account data."""
    # Create a CUSTOMER_SUPPORT user for ACCT-001 (Northstar Logistics)
    northstar_user = UserContext(
        user_id="contact-northstar",
        role="CUSTOMER_SUPPORT",
        authorised_accounts=["ACCT-001"]
    )
    
    with active_user(northstar_user):
        # 1. Lookups for ACCT-001 should succeed
        acct = lookup_account("ACCT-001")
        assert acct is not None
        assert "error" not in acct
        assert acct["account_name"] == "Northstar Logistics"
        
        # ORD-1001 belongs to ACCT-001
        order = lookup_order("ORD-1001")
        assert order is not None
        assert "error" not in order
        assert order["order_id"] == "ORD-1001"
        
        # TKT-501 belongs to ACCT-001
        ticket = lookup_ticket("TKT-501")
        assert ticket is not None
        assert "error" not in ticket
        assert ticket["ticket_id"] == "TKT-501"
        
        # 2. query_operational_data should silently filter out other accounts
        all_accounts = query_operational_data("accounts")
        assert len(all_accounts) == 1
        assert all_accounts[0]["account_id"] == "ACCT-001"
        
        # Orders query should only return ACCT-001 orders
        all_orders = query_operational_data("orders")
        assert len(all_orders) > 0
        assert all(o["account_id"] == "ACCT-001" for o in all_orders)

def test_unauthorized_access_rejected():
    """Verify that a user is blocked from accessing other accounts' data."""
    # Create a CUSTOMER_SUPPORT user for ACCT-001 (Northstar Logistics)
    northstar_user = UserContext(
        user_id="contact-northstar",
        role="CUSTOMER_SUPPORT",
        authorised_accounts=["ACCT-001"]
    )
    
    with active_user(northstar_user):
        # --- Data Layer Checks (Should raise PermissionError) ---
        with pytest.raises(PermissionError) as excinfo:
            op_lookup_account("ACCT-002")
        assert "is not authorized" in str(excinfo.value)
        
        with pytest.raises(PermissionError):
            op_lookup_order("ORD-2002")
            
        with pytest.raises(PermissionError):
            op_lookup_ticket("TKT-502")
            
        with pytest.raises(PermissionError):
            op_calculate_service_credit("ORD-2002")
            
        # --- Agent Tool Layer Checks (Should return graceful error dictionary) ---
        res_acct = lookup_account("ACCT-002")
        assert "error" in res_acct
        assert "Access Denied" in res_acct["error"]
        
        res_order = lookup_order("ORD-2002")
        assert "error" in res_order
        assert "Access Denied" in res_order["error"]
        
        res_ticket = lookup_ticket("TKT-502")
        assert "error" in res_ticket
        assert "Access Denied" in res_ticket["error"]
        
        res_credit = calculate_service_credit("ORD-2002")
        assert "error" in res_credit
        assert "Access Denied" in res_credit["error"]
        
        # Escalation for TKT-502 should fail (returns dictionary with success=False or throws if input checks fail)
        res_escalate = create_escalation("TKT-502", "P1", "Unauthorised escalation attempt")
        assert res_escalate["success"] is False
        assert "Access Denied" in res_escalate["error"]

def test_bypass_protection_fails():
    """Verify that if no user context is active, access is denied (Secure by Default)."""
    # Temporarily set context to None
    with active_user(None):
        # --- Data Layer Checks (Should raise PermissionError) ---
        with pytest.raises(PermissionError) as excinfo:
            op_lookup_account("ACCT-001")
        assert "No active user context set" in str(excinfo.value)
        
        with pytest.raises(PermissionError):
            op_lookup_order("ORD-1001")
            
        with pytest.raises(PermissionError):
            op_lookup_ticket("TKT-501")
            
        with pytest.raises(PermissionError):
            query_operational_data("orders")
            
        with pytest.raises(PermissionError):
            op_calculate_service_credit("ORD-2002")
            
        # --- Agent Tool Layer Checks (Should return graceful error dictionary) ---
        res_acct = lookup_account("ACCT-001")
        assert "error" in res_acct
        assert "No active user context set" in res_acct["error"]
        
        res_order = lookup_order("ORD-1001")
        assert "error" in res_order
        assert "No active user context set" in res_order["error"]
        
        res_ticket = lookup_ticket("TKT-501")
        assert "error" in res_ticket
        assert "No active user context set" in res_ticket["error"]
        
        res_credit = calculate_service_credit("ORD-2002")
        assert "error" in res_credit
        assert "No active user context set" in res_credit["error"]
        
        res_escalate = create_escalation("TKT-501", "P1", "Bypass escalation attempt")
        assert res_escalate["success"] is False
        assert "No active user context set" in res_escalate["error"]
