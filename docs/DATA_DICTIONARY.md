# ParcelPilot AI — Data Dictionary

This document provides a comprehensive overview of the assessment dataset for **ParcelPilot AI**. It outlines the authority, structure, and constraints of both the unstructured policy documents (PDFs) and the structured database sheets (Excel).

---

## 1. Unstructured Documents (PDFs)

These documents define support SLAs, standard operating procedures, and customer-specific contract overrides. 

According to [Support Policy v3 Section 1](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/01_Support_Policy_v3_CURRENT.pdf), the order of precedence in case of conflicts is:
1. **Signed Customer Agreements** (highest authority)
2. **Current Support Policy**
3. **Current Product Operations Guide / SOPs**
4. **Historical Tickets / Internal Notes** (lowest authority; context only, may contain incorrect information)

| Filename | Document Type | Title / Version | Status / Effective Date | Authority & Reliability | Key Content Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [`01_Support_Policy_v3_CURRENT.pdf`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/01_Support_Policy_v3_CURRENT.pdf) | Support Policy | ParcelPilot Support Policy v3 | **CURRENT**<br>Effective: 1 May 2026 | **High (Standard default)**.<br>Supersedes v2. Overridden only by custom signed customer agreements. | Defines P1/P2/P3 severity levels and default first-response SLA targets for Enterprise, Growth, and Standard plans. Specifies immediate escalation for P1 incidents and explicit statement of SLA breaches. |
| [`02_Support_Policy_v2_DEPRECATED.pdf`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/02_Support_Policy_v2_DEPRECATED.pdf) | Support Policy | ParcelPilot Support Policy v2 | **DEPRECATED**<br>Effective: 1 Jan 2025 | **None for active requests**.<br>Retained for historical reference only. | Contains outdated severity targets. Must not be used for current SLA evaluations. |
| [`03_Cancellation_and_Service_Credit_SOP_v4.pdf`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/03_Cancellation_and_Service_Credit_SOP_v4.pdf) | SOP | ParcelPilot Cancellation & Service Credit SOP v4 | **CURRENT**<br>Effective: 15 June 2026 | **High (Standard default)**.<br>Subject to overrides by signed customer agreements. | Outlines cancellation terms based on shipment state (DRAFT, BOOKED, PICKED_UP, DELIVERED). Defines default failed-pickup credit (lower of INR 500 or 10% of fee) and limits individual credit approvals above INR 1,000 to manager approval. |
| [`04_Product_Operations_Guide_and_Known_Issues.pdf`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/04_Product_Operations_Guide_and_Known_Issues.pdf) | Ops Guide | ParcelPilot Product Operations Guide | **CURRENT**<br>Updated: 14 Aug 2026 | **High (Product truth)**.<br>Indicates current platform status, limitations, and workarounds. | Outlines plan capabilities (e.g. bulk upload available for Growth/Enterprise, max 5,000 rows). Lists open known issues: KI-208 (CSV uploads > 3,000 rows fail; workaround split files) and KI-211 (SwiftShip webhook delay up to 20 mins). |
| [`05_Northstar_Logistics_Enterprise_Agreement.pdf`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/05_Northstar_Logistics_Enterprise_Agreement.pdf) | Customer Agreement | ParcelPilot - Northstar Logistics Enterprise Agreement | **ACTIVE (Customer-Specific)**<br>Term: 1 Jan 2026 to 31 Dec 2026 | **Highest for ACCT-001**.<br>Overrides all standard support and cancellation policies. | Custom SLA targets: P1 (15 min, 24x7), P2 (1 hour), P3 (8 business hours). Waives all cancellation fees for BOOKED shipments prior to carrier pickup. Caps monthly service credits at INR 5,000. |
| [`06_LumenWorks_Service_Agreement.pdf`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/06_LumenWorks_Service_Agreement.pdf) | Customer Agreement | ParcelPilot - LumenWorks Service Agreement | **ACTIVE (Customer-Specific)**<br>Term: 1 Mar 2026 to 28 Feb 2027 | **Highest for ACCT-002**.<br>Overrides standard failed-pickup credits. | Outlines specific support response times (P1: 2 business hours, P2: 4 business hours, P3: 2 business days; no weekend/after-hours). Custom credit: fixed INR 300 credit for missed pickups > 4 hours late where carrier is at fault. |

---

## 2. Structured Assessment Data

The structured data is located in [`ParcelPilot_Assessment_Data.xlsx`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/ParcelPilot_Assessment_Data.xlsx). It contains four sheets defining accounts, orders, support tickets, and metadata.

### Dataset Metadata
*   **Dataset Snapshot Time**: `2026-08-16 11:00 Asia/Kolkata` (IST)
*   **Base Currency**: `INR`
*   **General Note**: Synthetic data representing a snapshot of support operations. Some historical closed tickets contain incorrect resolutions and must not be used as policy authority.

---

### Sheet 1: `README`
Contains basic metadata for the dataset snapshot.

| Column | Type | Description |
| :--- | :--- | :--- |
| **Key** (Col A) | String | Metadata key name (e.g. `Dataset snapshot`, `Currency`, `Notes`, `Important`) |
| **Value** (Col B) | String | Metadata value |

---

### Sheet 2: `accounts`
Stores information on registered customer accounts and reference keys to their custom contracts.

| Column | Type | Key | Description / Validation Constraints |
| :--- | :--- | :--- | :--- |
| `account_id` | String | **Primary Key** | Unique account identifier format `ACCT-###` (e.g. `ACCT-001`). |
| `account_name` | String | | Name of the customer organization. |
| `plan` | String | | Service subscription plan. Allowed values: `Enterprise`, `Growth`, `Standard`. |
| `status` | String | | Account status (e.g. `active`). |
| `csm` | String | | Customer Success Manager assigned to this account. |
| `contract_file` | String / Null | | Name of the customer's active contract PDF file, or `None` if standard policies apply. |
| `premium_support` | Boolean | | Indicates if the account has custom high-priority support SLA terms enabled. |
| `notes` | String | | Contextual details regarding custom agreements or general account status. |

---

### Sheet 3: `orders`
Stores order records, scheduled logistics windows, and pickup metrics.

| Column | Type | Key | Description / Validation Constraints |
| :--- | :--- | :--- | :--- |
| `order_id` | String | **Primary Key** | Unique order ID format `ORD-####` (e.g. `ORD-1001`). |
| `account_id` | String | **Foreign Key** | References `accounts.account_id`. |
| `carrier` | String | | Name of the shipping provider (e.g. `SwiftShip`, `BlueDart Pro`, `RoadRunner`). |
| `status` | String | | Current order status. Allowed values: `DRAFT`, `BOOKED`, `PICKED_UP`, `DELIVERED`. |
| `booked_at` | Datetime / String | | Timestamp when order was booked (`YYYY-MM-DD HH:MM`). |
| `pickup_window_start` | Datetime / String | | Scheduled start time of the carrier pickup window. |
| `pickup_window_end` | Datetime / String | | Scheduled end time of the carrier pickup window. |
| `pickup_actual_at` | Datetime / String / Null | | Actual timestamp when carrier pickup was confirmed. Null if not yet picked up. |
| `shipment_fee_inr` | Float | | Cost of the shipment in Indian Rupees (INR). |
| `carrier_fault` | Boolean | | True if carrier was responsible for an operational delay or missed window. |
| `customer_fault` | Boolean | | True if customer was responsible for an operational delay or missed window. |
| `cancellation_requested_at`| Datetime / String / Null | | Timestamp when customer submitted a cancellation request. Null if not requested. |
| `notes` | String | | Operational logs, customer request contexts, and status summaries. |

---

### Sheet 4: `tickets`
Stores support tickets opened by customers, current ownership, and resolution logs.

| Column | Type | Key | Description / Validation Constraints |
| :--- | :--- | :--- | :--- |
| `ticket_id` | String | **Primary Key** | Unique ticket ID format `TKT-###` (e.g. `TKT-501`). |
| `account_id` | String | **Foreign Key** | References `accounts.account_id`. |
| `created_at` | Datetime / String | | Timestamp when support ticket was opened (`YYYY-MM-DD HH:MM`). |
| `status` | String | | Ticket operational status. Allowed values: `open`, `closed`. |
| `subject` | String | | Brief summary of the customer's query or issue. |
| `description` | String | | Detailed textual description of the issue. |
| `channel` | String | | Support communication channel. Allowed values: `email`, `chat`. |
| `assigned_to` | String | | Name of the support representative assigned to the ticket (e.g. `Rohit`, `Maya`). |
| `last_customer_message_at`| Datetime / String | | Timestamp of the last inbound customer message. |
| `historical_resolution`| String / Null | | Recorded resolution for closed tickets. **Warning**: Historical agent resolutions may conflict with active policies and contracts. |

---

## 3. Policy Conflicts & Data Discrepancies Identified

During the audit, the following conflicts between current policy/contract documents and the historical ticket records/active orders were identified:

1.  **SLA Breaches on Active Tickets**:
    *   [`TKT-505`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/ParcelPilot_Assessment_Data.xlsx) (Axis Labs - ACCT-004) reports a "Possible API key exposure". Per [Support Policy v3 Section 2](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/01_Support_Policy_v3_CURRENT.pdf), a confirmed or suspected credential exposure is a **P1 - Critical** severity incident. Axis Labs is on the standard **Enterprise** plan, which has a default P1 response target of **30 minutes, 24x7**. The ticket was created at `08:30` (last customer message at `09:10`), and at the dataset snapshot (`11:00`), it is still open and unescalated, resulting in a severe **SLA breach** (~2.5 hours elapsed).
    *   [`TKT-501`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/ParcelPilot_Assessment_Data.xlsx) (Northstar Logistics - ACCT-001) reports "All shipment creation is failing", which is a complete production outage preventing all shipment creation (**P1 - Critical** severity). Northstar's contract specifies a **15-minute, 24x7** response target. The ticket was created at `10:30`, and by `11:00` (snapshot time), it remains open for 30 minutes, which constitutes an **SLA breach**.
2.  **Incorrect Historical Ticket Resolutions**:
    *   [`TKT-450`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/ParcelPilot_Assessment_Data.xlsx) (Northstar Logistics - ACCT-001, closed): The agent told the customer an INR 250 cancellation fee applied for a cancellation requested 90 minutes after booking (prior to pickup). However, the [Northstar Enterprise Agreement Section 2](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/05_Northstar_Logistics_Enterprise_Agreement.pdf) explicitly states that Northstar may cancel any booked shipment before pickup with **no cancellation fee**, regardless of booking timing. The historical resolution was incorrect.
    *   [`TKT-451`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/ParcelPilot_Assessment_Data.xlsx) (LumenWorks - ACCT-002, closed): The agent stated that the Growth plan only supports bulk upload files up to 3,000 rows. However, the [Product Operations Guide Section 1](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/04_Product_Operations_Guide_and_Known_Issues.pdf) clearly indicates that Growth supports CSV files up to **5,000 rows**, but notes a known platform bug (KI-208) causing intermittent failures above 3,000 rows. The agent miscommunicated a temporary platform bug as a permanent plan constraint.
3.  **Active Order Status & Known Issues**:
    *   [`TKT-504`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/ParcelPilot_Assessment_Data.xlsx) (Northstar Logistics - ACCT-001, open) complains that order [`ORD-1002`](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/ParcelPilot_Assessment_Data.xlsx) shows BOOKED after driver pickup. This matches **KI-211** (SwiftShip Webhook Delay) from the [Product Operations Guide](file:///C:/Users/agrav/.gemini/antigravity-ide/scratch/parcelpilot-ai/data/raw/04_Product_Operations_Guide_and_Known_Issues.pdf), which warns that confirmation webhooks can arrive up to 20 minutes late.
