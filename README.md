# ParcelPilot AI — Trust-Aware Support Operations Agent

> [!NOTE]
> This is a Minimum Viable Product (MVP) designed and implemented within a time-constrained assessment window for the CalQuity AI Engineer position.

**ParcelPilot AI** is a trust-aware support intelligence platform for logistics operations. It assists Support Operators by combining unstructured document RAG (agreements, SOPs) with structured database operations (accounts, orders, tickets) while enforcing strict access boundaries and human-in-the-loop validation for state-changing database actions.

---

## Features

1.  **Trust-Aware Policy Extraction (RAG)**: Retrieves relevant policy passages from unstructured handbooks and customer service agreements.
2.  **Structured Database Actions**: Safe querying of order statuses, ticket logs, and service credit eligibility.
3.  **Strict Security Boundaries**: Verification of account boundaries inside the tool execution layer, ensuring operators only see records they are explicitly authorized to access.
4.  **Stateful Human-in-the-Loop (HITL) Approvals**: Escalations are proposed in memory and must be manually approved or dismissed by the operator before any database mutations are written.
5.  **Conflict Resolution Engine**: Evaluates source reliability and resolves rule discrepancies (e.g., custom enterprise contracts overriding standard standard policies) with dynamic confidence scoring (`HIGH`/`MEDIUM`/`LOW`).
6.  **Interactive Operations Dashboard**: A Streamlit interface displaying user profiles, system health indicators, real-time tool badges, and suggested hiring scenario click-shortcuts.

---

## Tech Stack

*   **Frontend**: Streamlit
*   **AI Engine**: Gemini Python SDK (`google-genai` model `gemini-2.5-flash`)
*   **Database**: SQLite (SQL query parameter binding for injection prevention)
*   **Vector Search Engine**: Clean NumPy Cosine Similarity over SentenceTransformer embeddings (offline index cached as `.pkl`)
*   **Text Processing**: `PyPDF2` (structured PDF loader and metadata extractor)
*   **Testing Suite**: `pytest` (mocked execution and auth state validators)

---

## Project Structure

```text
parcelpilot-ai/
├── app.py                      # Main Streamlit Dashboard UI
├── agent/
│   ├── agent.py                # Core AI Agent, Mock fallbacks, and System Instructions
│   └── approval_state.py       # Stateful HITL Escalation Proposals Manager
├── tools/
│   └── agent_tools.py          # Unified Agent tools and security decorators
├── rag/
│   └── rag_retrieval.py        # PDF extraction, chunker, vector search engine
├── data/
│   └── raw/                    # Raw unstructured assessment files (.pdf, .xlsx)
├── db/
│   ├── db_setup.py             # SQLite DB schemas and CSV loaders
│   └── parcelpilot.db          # Active operations database
├── utils/
│   └── auth.py                 # Mock Authentication context and boundary utilities
├── tests/                      # pytest automated validation suites
├── docs/
│   ├── DATA_DICTIONARY.md      # Field mapping and document reliability records
│   └── ARCHITECTURE.md         # Detailed architectural documentation
└── requirements.txt            # Dependency file
```

---

## Setup & Local Run

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Load & Process Reference Data
To process the raw PDF policy documents and Excel operational workbook supplied in the assessment:
```powershell
# Parse PDFs and construct the offline vector search index
python -c "from rag.rag_retrieval import build_index; build_index()"

# Load Excel worksheets and construct the SQLite database
python -c "from db.db_setup import setup_database; setup_database()"
```
*(Note: These build tasks are run automatically if no cache files are found when starting the agent or running tests).*

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and configure your API key:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Launch the Operations Console
```powershell
python -m streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Running Tests

Verify the operational constraints, tools layer, access permissions, and trust scoring:
```powershell
python -m pytest tests/
```

---

## Suggested Demo Scenarios (Shortcuts Available in UI)

When the dashboard history is cleared, three interactive shortcuts are rendered to execute the core assessment scenarios immediately:

1.  **Scenario A (Fee Cancellation Waiver)**: Click `📋 Cancel ORD-1001?` to run the query *"Can Northstar cancel ORD-1001 without a cancellation fee? Explain why."* 
    *   *Result*: Evaluates Northstar's booked cancellation query, detects standard fee rules vs. custom enterprise contract, resolves the override, cites `05_Northstar_Logistics_Enterprise_Agreement.pdf` (precedence 1), and returns `🟢 HIGH CONFIDENCE`.
2.  **Scenario B (Service Credit Delay Check)**: Click `⏱️ Late Pickup Credit?` to run the query *"A pickup is three hours late because of carrier fault. Should I get a service credit? Explain if this applies to all accounts."*
    *   *Result*: Resolves that while default rules award credits for delays > 2 hours, LumenWorks' custom contract overrides standard thresholds (requiring delay > 4 hours). Evaluates credit rules and cites resolved document overrides.
3.  **Scenario C (Ticket Investigation & Escalation Approval)**: Click `🎫 Escalate TKT-505?` to run the query *"Review ticket TKT-505 and escalate it."*
    *   *Result*: Evaluates Axis Labs' ticket `TKT-505`, matches the API key exposure incident description, classifies it as severity `P1` (target response time 30 mins) under current policy, detects a 2.5-hour response delay breach, and prepares an in-memory **Escalation Proposal** prompting the operator for approval.

---

## Known Limitations

*   **Gemini Cloud Project Restraints**: The configured cloud project has the `Generative Language API` disabled, returning 403 authorization errors. A local mock engine router has been implemented inside `agent.py` to route target queries, execute underlying tools, and verify output boundaries without relying on live API responses.
*   **Excel Source Synchronization**: Database loader parses spreadsheet snapshots statically. Real-time updates to Excel files require executing the DB setup script again to re-sync SQLite rows.
