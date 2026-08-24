# Product Note — ParcelPilot AI

This note details the product decisions, strategic feature inclusions, trade-offs, next-stage features, and evaluation metrics for the **ParcelPilot AI** platform.

---

## 1. Additional Client Problem Addressed

We addressed the **Operational Incident Severity Escalation Loop** by building a **Human-in-the-Loop (HITL) Stateful Escalation Portal**. 

When customer support tickets breach SLA response targets (e.g. Axis Labs' 2.5-hour delay on a P1 critical credential leak), standard bots either do nothing or immediately trigger automated notifications. Automated escalations without operator oversight frequently trigger false alarms, causing alarm fatigue and operational chaos. Conversely, completely manual escalations are slow and error-prone.

By pairing AI-driven RAG analysis (detecting SLA breaches) with a stateful confirmation card in the operator's chat window, we bridge this gap: the agent handles the analysis and populates the ticket metadata, but the operator retains control over execution.

---

## 2. Why It Was Chosen

This feature was chosen because support operators are the primary gatekeepers of customer trust. In high-stakes business environments (e.g. credential exposure, premium tier SLA breaches), giving an AI model direct write access to change ticket priorities, assign engineers, or award credits represents a major operational risk. Securing this boundary with a stateful proposal dashboard:
- Eliminates execution risk while accelerating operator workflows.
- Establishes a clean audit trail of who approved each database change.
- Keeps the agent's permissions read-only for general operations, requiring conscious consent for write mutations.

---

## 3. What Would Be Built Next

1.  **OAuth & Role-Based Authorization Integration**: Replace the mock authentication context with active JWT-based auth tokens linked to enterprise identity providers (Okta/Active Directory), allowing fine-grained row-level filters in SQLite.
2.  **Live Slack / PagerDuty Integration**: Trigger instant channels alerts when escalations are confirmed.
3.  **Dynamic Vector Index Syncing**: Create database triggers that automatically update the vector index when new customer agreements are uploaded, removing manual processing steps.
4.  **Auto-Suggested Credit Settlements**: Expand the service credit calculator to draft credit proposals alongside escalations, allowing operators to confirm credits directly from the chat interface.

---

## 4. What Was Intentionally Left Out

*   **Multi-tenant Database Clusters**: We chose a single local SQLite database instead of Postgres/MySQL to keep setup lightweight, simple, and dependency-free.
*   **Arbitrary Prompt Conversational Chat**: We bypassed general chat handling (e.g. jokes, unrelated prompts) to focus engineering resources strictly on reliable operational tool execution.
*   **Online Embedding API Calls**: We avoided calling online OpenAI/Vertex AI embedding endpoints to prevent API quota issues and network latency.

---

## 5. Metric for Product Usefulness

### **SLA Breach Mitigation Rate (SBMR)**

$$\text{SBMR} = \frac{\text{SLA incidents identified and escalated within } 15 \text{ minutes of breach}}{\text{Total SLA breach incidents logged}}$$

This metric tracks how quickly the system flags delayed critical issues and prompts operators to escalate them. A high SBMR directly correlates with reduced contract penalties, lower customer churn, and optimized support resource distribution.
