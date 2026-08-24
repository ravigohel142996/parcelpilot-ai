# Technical Architecture — ParcelPilot AI

This document provides a detailed breakdown of the architectural design, security boundaries, trust verification routines, and technical trade-offs of the **ParcelPilot AI** MVP.

---

## 1. Agent Design

The agent is designed as a **ReAct (Reasoning and Action) Loop** powered by Gemini.
*   **Prompt-Driven Workflows**: The system prompt instructs the agent to analyze user intent, identify required database inputs, call the minimal set of tools needed, resolve document priority conflicts, and output structured reasoning.
*   **Constraint Enforcement**: The system instructions explicitly restrict the model from directly accessing database files or guessing parameters.
*   **Offline Fallback Mode**: Due to cloud project API key restrictions (403 errors), the agent employs a local deterministic mock router. The router intercepts standard scenario strings, executes the exact underlying database and RAG tools, and formats identical trust-aware output metadata dictionaries.

---

## 2. Tool Design

Tools act as the secure interface between the AI reasoning layer and the persistence layer.
*   **Unified Interface**: All endpoints (`lookup_order`, `lookup_ticket`, `propose_escalation`, etc.) are exposed as strongly typed Python functions with validation.
*   **Input Validation**: Inputs are validated (e.g. ticket ID structures, empty fields, and priority ranges) before database execution to prevent injection or corruption.
*   **Access-Checked Wrapper**: Every operational lookup is wrapped in security checks, raising `PermissionError` immediately if the requested record falls outside the operator's account visibility scope.

---

## 3. RAG / Document Handling

The unstructured data layer reads and indexes policy documents:
*   **Text Extraction**: Parses reference PDFs (`Support Policy`, `SOPs`, and `Signed Customer Agreements`) using `PyPDF2` while extracting filename and version metadata.
*   **Chunking Strategy**: Splits text into 500-character segments with 100-character overlaps, appending metadata (filename, version, customer name, status) to each chunk.
*   **Vector Index**: Computes embeddings using SentenceTransformer. Similarity matches are performed offline using NumPy Cosine Similarity, sorting results by score.

---

## 4. Structured Data Handling

Structured worksheets (Accounts, Orders, Tickets) are migrated from the assessment Excel workbook to a local SQLite database:
*   **Initialization**: Reads reference tables during build and maps columns to SQLite types.
*   **Parameterized Queries**: All lookups query SQLite using parameter bindings to enforce SQL-injection safety.
*   **Service Credit Calculations**: The calculator verifies delay fault records and applies policy thresholds (default SOP 2-hour delay threshold vs. custom contract overrides) on the database results.

---

## 5. Access Control

Security is enforced at the data layer, not the LLM prompt layer:
*   **UserContext**: Active operator session encapsulates `user_id`, `role`, and `authorized_accounts`.
*   **Authorized Scope Verification**: Before any tool queries SQLite, it verifies that the requested record's `account_id` matches the session's list of `authorized_accounts` (or the wildcard `*` granted to Support Operations). Unauthorized attempts raise a `PermissionError` and return empty structures, preventing prompt injection bypasses.

---

## 6. Source Reliability & Conflict Handling

A rules-based trust engine resolves contradictions across retrieved sources:
*   **Precedence Hierarchy**:
    1.  Customer-Specific signed agreements
    2.  Current support policy
    3.  Current SOP (Standard Operating Procedure)
    4.  Product operations documentation
    5.  Deprecated policies
    6.  Historical ticket resolutions
*   **Conflict Detection**: When the RAG retrieval finds standard policy rules alongside a customer agreement override, the engine:
    *   Flags `conflict_detected = True`
    *   Selects the highest precedence contract as the `authoritative_source`
    *   Details the discrepancy in `conflict_details`
    *   Returns a `HIGH` confidence score once resolved.
*   **Escalation Fallback**: If retrieved info is conflicting or insufficient (e.g., missing database keys or policy gaps), confidence drops to `LOW`, and the agent recommends manual human review instead of generating an answer.

---

## 7. Confirmation Workflow

State-changing actions (e.g. ticket escalations) enforce operator consent before database mutation:
*   **Proposal Stage**: The agent creates an in-memory proposal containing the ticket, priority, and reason, returning a recommendation without modifying database state.
*   **State Manager**: Stores proposals in a session-aware proxy (binding to Streamlit's `st.session_state` or a thread-safe `ContextVar` during tests).
*   **Execution Stage**: Once the operator clicks "Confirm Escalation" in the dashboard card, the proposal is retrieved, verified, written to the SQLite escalations table, and the ticket status is updated to `'escalated'`. If dismissed, the proposal is discarded, leaving the database unchanged.

---

## 8. Technical Trade-Offs

1.  **SQLite vs. Production Postgres**: SQLite was selected for rapid setup, thread safety, and zero external dependency footprint, matching assessment timeframes.
2.  **SentenceTransformer vs. Cloud Embeddings APIs**: Local text vector embeddings ensure 100% offline functionality, eliminating latency, api quota cost, and connection failures.
3.  **Local Mock Agent Router**: Bypasses active API key 403 blocks to prove tool and pipeline correctness, trading off general arbitrary conversation capability for robust scenario verification.
