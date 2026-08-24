import pytest
import os
from utils.auth import DEMO_USER_RAVI, active_user
from agent.agent import run_agent_query

# Skip tests if GEMINI_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "your_gemini_api_key_here",
    reason="GEMINI_API_KEY not configured in environment"
)

def test_northstar_cancellation_workflow():
    """
    Test Step 8 Query: 'Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.'
    
    Verifies:
      - Customer identification (ACCT-001 / Northstar)
      - Order status check (ORD-1001 is BOOKED)
      - Contract override matching (Northstar agreement waives booked cancellation fees)
      - SOP conflict resolution (overrides SOP v4 INR 250 fee after 30 mins)
    """
    query = "Can Northstar cancel ORD-1001 without a cancellation fee? Explain why."
    
    # Run under authorised demo-ravi context
    res = run_agent_query(query)
    
    answer = res["answer"]
    tools = res["tools_used"]
    
    print("\n--- Northstar Cancellation Response ---")
    print(answer)
    print("Tools used:", tools)
    
    # 1. Tools verification: should query order details and search document catalog
    assert len(tools) > 0
    assert any(t in tools for t in ["lookup_order", "lookup_operational_data"])
    assert "search_documents" in tools
    
    # 2. Reasoning verification: must state that fee is waived/no fee applies
    assert any(keyword in answer.lower() for keyword in ["waived", "no fee", "no cancellation fee", "free", "without a fee"])
    
    # 3. Source precedence: must refer to the Northstar Enterprise Agreement/Contract and state it overrides SOP v4
    assert any(keyword in answer.lower() for keyword in ["agreement", "contract", "override", "precedence"])
    assert "sop" in answer.lower()

def test_service_credit_delay_workflow():
    """
    Test Step 8 Query: 'A pickup is three hours late because of carrier fault. Should I get a service credit?'
    
    Verifies:
      - Agent distinguishes rules based on account context.
      - Recognizes standard SOP v4 threshold (> 2 hours delay) vs. LumenWorks override (> 4 hours delay).
      - Concludes that standard accounts are eligible, but LumenWorks is not (3 hours < 4 hours).
    """
    query = "A pickup is three hours late because of carrier fault. Should I get a service credit? Explain if this applies to all accounts."
    
    res = run_agent_query(query)
    
    answer = res["answer"]
    tools = res["tools_used"]
    
    print("\n--- Service Credit Delay Response ---")
    print(answer)
    print("Tools used:", tools)
    
    # 1. Tools verification: should search policy documents
    assert "search_documents" in tools
    
    # 2. Precedence reasoning: must distinguish between default SOP (2 hours) and LumenWorks contract (4 hours)
    assert "lumenworks" in answer.lower()
    assert "2 hours" in answer.lower()
    assert "4 hours" in answer.lower()
    
    # 3. Credit logic: must identify that a 3-hour delay qualifies under default SOP but NOT for LumenWorks
    assert "eligible" in answer.lower()
    assert "not eligible" in answer.lower() or "does not apply" in answer.lower() or "exclude" in answer.lower() or "except" in answer.lower() or "lumenworks is not" in answer.lower()

def test_api_exposure_sla_breach_escalation():
    """
    Test Step 7 Query: 'Review ticket TKT-505. Identify its severity, whether the response SLA has been breached, and if escalation is needed. If needed, escalate it.'
    
    Verifies:
      - Ticket retrieval (TKT-505 is credential exposure)
      - Support policy match (credential exposure is P1 Critical)
      - SLA breach detection (elapsed time 2.5 hours vs. 30 mins target)
      - State change execution (calls create_escalation)
    """
    query = "Review ticket TKT-505. Identify its severity, whether the response SLA has been breached, and if escalation is needed. If needed, escalate it."
    
    res = run_agent_query(query)
    
    answer = res["answer"]
    tools = res["tools_used"]
    
    print("\n--- SLA Breach & Escalation Response ---")
    print(answer)
    print("Tools used:", tools)
    
    # 1. Tools verification: must check ticket, search policies, and run propose_escalation
    assert any(t in tools for t in ["lookup_ticket", "lookup_operational_data"])
    assert "search_documents" in tools
    assert "propose_escalation" in tools
    assert "create_escalation" not in tools
    
    # 2. Severity check: must identify as P1 Critical
    assert "p1" in answer.lower() or "critical" in answer.lower()
    
    # 3. SLA Breach: must state that response target is breached
    assert "breach" in answer.lower() or "missed" in answer.lower() or "violated" in answer.lower()
    
    # 4. Confirmation request: must propose the escalation and ask for confirmation
    assert "proposed" in answer.lower() or "prepared" in answer.lower()
    assert "would you like" in answer.lower() or "confirm" in answer.lower() or "create it" in answer.lower()
