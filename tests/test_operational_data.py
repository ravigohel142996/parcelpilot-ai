import pytest
import sqlite3
from unittest.mock import patch
from tools.operational_data import (
    lookup_account,
    lookup_order,
    lookup_ticket,
    query_operational_data,
    calculate_service_credit
)

def test_valid_lookups():
    """Verify that looking up valid IDs returns correct information."""
    account = lookup_account("ACCT-001")
    assert account is not None
    assert account["account_name"] == "Northstar Logistics"
    assert account["plan"] == "Enterprise"
    
    order = lookup_order("ORD-1001")
    assert order is not None
    assert order["account_id"] == "ACCT-001"
    assert order["carrier"] == "SwiftShip"
    
    ticket = lookup_ticket("TKT-501")
    assert ticket is not None
    assert ticket["account_id"] == "ACCT-001"
    assert ticket["assigned_to"] == "Rohit"

def test_missing_records():
    """Verify that looking up non-existent records returns None."""
    assert lookup_account("ACCT-999") is None
    assert lookup_order("ORD-9999") is None
    assert lookup_ticket("TKT-999") is None

def test_invalid_lookups():
    """Verify that looking up malformed or dangerous IDs throws a ValueError."""
    # Malformed patterns
    with pytest.raises(ValueError):
        lookup_account("invalid_id")
        
    with pytest.raises(ValueError):
        lookup_order("ORD-abc")
        
    with pytest.raises(ValueError):
        lookup_ticket("TKT-")
        
    # SQL injection attempts
    with pytest.raises(ValueError):
        lookup_account("ACCT-001' OR '1'='1")
        
    with pytest.raises(ValueError):
        lookup_order("ORD-1001; DROP TABLE orders;")

def test_query_operational_data_safety():
    """Verify whitelisting and parameterized safety in query_operational_data."""
    # Query with valid filters
    orders = query_operational_data("orders", {"account_id": "ACCT-001"})
    assert len(orders) == 2
    
    # Querying invalid tables should throw ValueError
    with pytest.raises(ValueError):
        query_operational_data("sqlite_master")
        
    # Querying with invalid column names should throw ValueError
    with pytest.raises(ValueError):
        query_operational_data("accounts", {"malicious_column": "some_value"})

def test_service_credit_calculations_existing_data():
    """Test credit calculations on the actual snapshot data."""
    # ORD-2002: LumenWorks, RoadRunner carrier_fault=True, window end 06:30, actual=None (snapshot 11:00)
    # Delay = 4.5 hours. LumenWorks threshold = 4.0 hours, fixed INR 300 credit.
    res = calculate_service_credit("ORD-2002")
    assert res["eligible"] is True
    assert res["credit_amount"] == 300.0
    assert res["delay_hours"] == 4.5
    assert "LumenWorks Contract" in res["rule_applied"]
    assert res["requires_manager_approval"] is False

    # ORD-4001: Axis Labs, SwiftShip, DELIVERED, carrier_fault=False.
    # Should not be eligible since carrier was not at fault.
    res_not_eligible = calculate_service_credit("ORD-4001")
    assert res_not_eligible["eligible"] is False
    assert res_not_eligible["credit_amount"] == 0.0
    assert "Carrier is not at fault" in res_not_eligible["reason"]

def test_service_credit_calculations_mocked_standard():
    """Test default SOP v4 credit calculations using mocked order/account lookups."""
    # Test Case 1: Standard account, carrier fault, delay of 3 hours (> 2 hours), fee is INR 3,000.
    # Default SOP credit = min(500, 10% of 3000) = INR 300.
    mock_order = {
        "order_id": "ORD-8001",
        "account_id": "ACCT-003",  # Beacon Retail (Standard, default SOP)
        "carrier": "SwiftShip",
        "status": "BOOKED",
        "booked_at": "2026-08-16 07:00",
        "pickup_window_start": "2026-08-16 08:00",
        "pickup_window_end": "2026-08-16 09:00",
        "pickup_actual_at": "2026-08-16 12:00",  # Actual pickup 3 hours late
        "shipment_fee_inr": 3000.0,
        "carrier_fault": 1,
        "customer_fault": 0,
        "cancellation_requested_at": None,
        "notes": "Test missed pickup"
    }
    
    mock_account = {
        "account_id": "ACCT-003",
        "account_name": "Beacon Retail",
        "plan": "Standard",
        "status": "active",
        "csm": "Neha Kapoor",
        "contract_file": None,
        "premium_support": 0,
        "notes": "Standard plan"
    }

    with patch("tools.operational_data.lookup_order", return_value=mock_order), \
         patch("tools.operational_data.lookup_account", return_value=mock_account):
        res = calculate_service_credit("ORD-8001")
        assert res["eligible"] is True
        assert res["credit_amount"] == 300.0  # 10% of 3000
        assert res["delay_hours"] == 3.0
        assert "Default SOP v4" in res["rule_applied"]

    # Test Case 2: High fee (INR 8,000), standard account, delay 3 hours (> 2 hours).
    # Default SOP credit = min(500, 10% of 8000) = INR 500 (capped).
    mock_order_high_fee = mock_order.copy()
    mock_order_high_fee["shipment_fee_inr"] = 8000.0
    
    with patch("tools.operational_data.lookup_order", return_value=mock_order_high_fee), \
         patch("tools.operational_data.lookup_account", return_value=mock_account):
        res = calculate_service_credit("ORD-8001")
        assert res["eligible"] is True
        assert res["credit_amount"] == 500.0  # min(500, 800)
        assert res["delay_hours"] == 3.0

    # Test Case 3: Delay <= 2 hours (e.g. 1.5 hours). Not eligible.
    mock_order_short_delay = mock_order.copy()
    mock_order_short_delay["pickup_actual_at"] = "2026-08-16 10:30"
    
    with patch("tools.operational_data.lookup_order", return_value=mock_order_short_delay), \
         patch("tools.operational_data.lookup_account", return_value=mock_account):
        res = calculate_service_credit("ORD-8001")
        assert res["eligible"] is False
        assert res["credit_amount"] == 0.0
        assert "Delay of 1.50 hours did not exceed the required threshold" in res["reason"]
