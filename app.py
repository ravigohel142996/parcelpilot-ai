import streamlit as st
import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page configuration first
st.set_page_config(
    page_title="ParcelPilot AI - Operations Dashboard",
    page_icon="📦",
    layout="wide",
)

# Custom Styling for Operations Dashboard
st.markdown("""
<style>
    .reportview-container {
        background: #F8F9FA;
    }
    .status-dot {
        height: 10px;
        width: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
    }
    .status-active {
        background-color: #2ECC71;
    }
    .status-inactive {
        background-color: #E74C3C;
    }
    .tool-badge {
        background-color: #EBF5FB;
        color: #2980B9;
        border: 1px solid #AED6F1;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-right: 5px;
        display: inline-block;
    }
    .card-proposal {
        background-color: #FEF9E7;
        border-left: 5px solid #F1C40F;
        border-radius: 4px;
        padding: 15px;
        margin: 10px 0;
    }
    .badge-confidence {
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 5px;
        display: inline-block;
    }
    .badge-high {
        background-color: #D4EFDF;
        color: #196F3D;
        border: 1px solid #A9DFBF;
    }
    .badge-medium {
        background-color: #FCF3CF;
        color: #7D6608;
        border: 1px solid #F9E79F;
    }
    .badge-low {
        background-color: #FADBD8;
        color: #78281F;
        border: 1px solid #F5B7B1;
    }
    .card-conflict {
        background-color: #FDEDEC;
        border-left: 5px solid #E74C3C;
        border-radius: 4px;
        padding: 12px;
        margin: 8px 0;
        color: #78281F;
        font-size: 0.85rem;
    }
    .source-citation {
        color: #7F8C8D;
        font-size: 0.8rem;
        font-style: italic;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

from utils.auth import DEMO_USER_RAVI, active_user
from agent.agent import run_agent_query
from agent.approval_state import (
    confirm_escalation,
    cancel_escalation,
    get_pending_escalation
)

# Tool badge mapping
TOOL_LABELS = {
    "search_documents": "🔎 Searching documents",
    "lookup_operational_data": "📊 Checking operational data",
    "lookup_order": "📦 Checking order details",
    "lookup_account": "🏢 Checking customer account",
    "lookup_ticket": "🎫 Checking ticket details",
    "calculate_service_credit": "🧮 Calculating service credit",
    "propose_escalation": "🎫 Preparing escalation proposal",
    "create_escalation": "🎫 Executing escalation"
}

def get_tool_badge(tool_name: str) -> str:
    return TOOL_LABELS.get(tool_name, f"🛠️ Executing {tool_name}")

def main():
    # Sidebar Profile Section
    st.sidebar.markdown("# 📦 PARCELPILOT AI")
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("User Profile")
    st.sidebar.markdown("**User:** Ravi")
    st.sidebar.markdown("**Role:** `Support Operations` (Wildcard)")
    st.sidebar.markdown("**Access:** `All Accounts (*)`")
    
    st.sidebar.markdown("---")
    
    # Sidebar Health Checks / System Status
    st.sidebar.subheader("System Status")
    
    # 1. Agent Engine health
    has_api_key = "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"] != ""
    agent_status = "status-active" if has_api_key else "status-inactive"
    agent_text = "Active" if has_api_key else "Missing API Key"
    st.sidebar.markdown(f'<span class="status-dot {agent_status}"></span> **Agent Engine:** {agent_text}', unsafe_allow_html=True)
    
    # 2. Document RAG health
    has_index = os.path.exists("db/vector_index.pkl")
    rag_status = "status-active" if has_index else "status-inactive"
    rag_text = "Active" if has_index else "Missing Index"
    st.sidebar.markdown(f'<span class="status-dot {rag_status}"></span> **Document RAG:** {rag_text}', unsafe_allow_html=True)
    
    # 3. Operational Data health
    has_db = os.path.exists("db/parcelpilot.db")
    db_status = "status-active" if has_db else "status-inactive"
    db_text = "Active" if has_db else "Missing DB"
    st.sidebar.markdown(f'<span class="status-dot {db_status}"></span> **Operational Data:** {db_text}', unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Clear Chat History", type="secondary"):
        st.session_state.messages = []
        with active_user(DEMO_USER_RAVI):
            cancel_escalation() # clear any pending approvals
        st.rerun()



    # Main Area Layout
    st.title("📦 ParcelPilot AI")
    st.markdown("*Trust-aware customer support intelligence*")
    st.markdown("---")
    
    # Initialize message list in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Render Chat Message logs or Welcome Empty State
    if not st.session_state.messages:
        # Welcome Empty State
        st.markdown("""
        <div style="background-color: #F8F9F9; border: 1px solid #EBEDEF; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <h3 style="margin-top: 0; color: #2C3E50; font-size: 1.25rem;">👋 Welcome to the ParcelPilot AI Operations Console</h3>
            <p style="color: #5D6D7E; margin-bottom: 12px; font-size: 0.95rem;">
                This internal support dashboard uses trust-aware reasoning and real-time database validation to assist Support Operators with orders, policies, and stateful approvals.
            </p>
            <p style="color: #7F8C8D; font-size: 0.85rem; margin-bottom: 8px;"><strong>Click a shortcut below to execute a hiring assessment scenario:</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📋 Cancel ORD-1001?", help="Northstar Cancellation fee scenario", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "Can Northstar cancel ORD-1001 without a cancellation fee? Explain why."})
                with st.spinner("Processing agent reasoning..."):
                    with active_user(DEMO_USER_RAVI):
                        agent_res = run_agent_query("Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.")
                        pending_esc = get_pending_escalation()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": agent_res["answer"],
                    "tools_used": agent_res["tools_used"],
                    "pending_escalation": pending_esc,
                    "confidence": agent_res.get("confidence", "HIGH"),
                    "authoritative_source": agent_res.get("authoritative_source", "None"),
                    "conflict_detected": agent_res.get("conflict_detected", False),
                    "conflict_details": agent_res.get("conflict_details", None)
                })
                st.rerun()
                
        with col2:
            if st.button("⏱️ Late Pickup Credit?", help="Carrier delay credit comparison", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "A pickup is three hours late because of carrier fault. Should I get a service credit? Explain if this applies to all accounts."})
                with st.spinner("Processing agent reasoning..."):
                    with active_user(DEMO_USER_RAVI):
                        agent_res = run_agent_query("A pickup is three hours late because of carrier fault. Should I get a service credit? Explain if this applies to all accounts.")
                        pending_esc = get_pending_escalation()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": agent_res["answer"],
                    "tools_used": agent_res["tools_used"],
                    "pending_escalation": pending_esc,
                    "confidence": agent_res.get("confidence", "HIGH"),
                    "authoritative_source": agent_res.get("authoritative_source", "None"),
                    "conflict_detected": agent_res.get("conflict_detected", False),
                    "conflict_details": agent_res.get("conflict_details", None)
                })
                st.rerun()
                
        with col3:
            if st.button("🎫 Escalate TKT-505?", help="API key breach escalation workflow", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "Review ticket TKT-505 and escalate it."})
                with st.spinner("Processing agent reasoning..."):
                    with active_user(DEMO_USER_RAVI):
                        agent_res = run_agent_query("Review ticket TKT-505 and escalate it.")
                        pending_esc = get_pending_escalation()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": agent_res["answer"],
                    "tools_used": agent_res["tools_used"],
                    "pending_escalation": pending_esc,
                    "confidence": agent_res.get("confidence", "HIGH"),
                    "authoritative_source": agent_res.get("authoritative_source", "None"),
                    "conflict_detected": agent_res.get("conflict_detected", False),
                    "conflict_details": agent_res.get("conflict_details", None)
                })
                st.rerun()
    else:
        # Render Chat Message logs
        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Show trust metadata and tool badges if present
                if msg["role"] == "assistant":
                    meta_html = ""
                    
                    # Confidence Pill
                    conf = msg.get("confidence", "HIGH").upper()
                    if conf == "HIGH":
                        meta_html += '<span class="badge-confidence badge-high">🟢 HIGH CONFIDENCE</span>'
                    elif conf == "MEDIUM":
                        meta_html += '<span class="badge-confidence badge-medium">🟡 MEDIUM CONFIDENCE</span>'
                    else:
                        meta_html += '<span class="badge-confidence badge-low">🔴 LOW CONFIDENCE</span>'
                        
                    # Tool badges
                    if msg.get("tools_used"):
                        for t in msg["tools_used"]:
                            meta_html += f'<span class="tool-badge">{get_tool_badge(t)}</span>'
                            
                    st.markdown(f'<div style="margin-top: 5px; margin-bottom: 5px;">{meta_html}</div>', unsafe_allow_html=True)
                    
                    # Conflict Warning Banner
                    if msg.get("conflict_detected"):
                        st.markdown(f"""
                        <div class="card-conflict">
                            <strong>⚠️ Policy Conflict Resolved:</strong> {msg.get('conflict_details')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                    # Authoritative Source Citation
                    auth_src = msg.get("authoritative_source")
                    if auth_src and auth_src != "None":
                        st.markdown(f'<div class="source-citation">📌 Authoritative Source: <strong>{auth_src}</strong></div>', unsafe_allow_html=True)
                    
                # Render Confirmation Widget if a proposal is pending in this message
                if msg["role"] == "assistant" and msg.get("pending_escalation"):
                    pending = msg["pending_escalation"]
                    st.markdown(f"""
                    <div class="card-proposal">
                        <h4 style="margin-top: 0; color: #7D6608;">🎫 Escalation Approval Required</h4>
                        <p style="margin-bottom: 5px;"><strong>Proposed Action:</strong> Create Escalation in Database</p>
                        <ul style="margin-top: 5px; margin-bottom: 5px; padding-left: 20px;">
                            <li><strong>Ticket ID:</strong> <code>{pending['ticket_id']}</code></li>
                            <li><strong>Priority:</strong> <code>{pending['priority']}</code></li>
                            <li><strong>Reason:</strong> {pending['reason']}</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button("Confirm Escalation", key=f"confirm_{pending['ticket_id']}_{idx}", type="primary"):
                            with active_user(DEMO_USER_RAVI):
                                res = confirm_escalation()
                            
                            # Add success response
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"✅ **Escalation Confirmed!** Ticket `{pending['ticket_id']}` has been successfully escalated to the `Escalation Team`.\n\n```json\n{res}\n```",
                                "tools_used": ["create_escalation"]
                            })
                            
                            # Clear pending on current message
                            msg["pending_escalation"] = None
                            st.rerun()
                    with col2:
                        if st.button("Cancel / Dismiss", key=f"cancel_{pending['ticket_id']}_{idx}", type="secondary"):
                            with active_user(DEMO_USER_RAVI):
                                res = cancel_escalation()
                                
                            # Add cancellation response
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"❌ **Escalation Proposal Cancelled.** No operational database changes were executed.",
                                "tools_used": []
                            })
                            
                            # Clear pending on current message
                            msg["pending_escalation"] = None
                            st.rerun()

    # Chat input and execution flow
    user_query = st.chat_input("Ask a question about orders, service credits, or support tickets...")
    
    if user_query:
        # Display user's message
        st.session_state.messages.append({
            "role": "user",
            "content": user_query
        })
        
        # Display spinner while reasoning
        with st.spinner("Processing agent reasoning..."):
            with active_user(DEMO_USER_RAVI):
                agent_res = run_agent_query(user_query)
                pending_esc = get_pending_escalation()
                
        # Append assistant's answer and tool list
        st.session_state.messages.append({
            "role": "assistant",
            "content": agent_res["answer"],
            "tools_used": agent_res["tools_used"],
            "pending_escalation": pending_esc,
            "confidence": agent_res.get("confidence", "HIGH"),
            "authoritative_source": agent_res.get("authoritative_source", "None"),
            "conflict_detected": agent_res.get("conflict_detected", False),
            "conflict_details": agent_res.get("conflict_details", None)
        })
        
        st.rerun()

if __name__ == "__main__":
    main()
