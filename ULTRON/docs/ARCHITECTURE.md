# ULTRON System Architecture

## 1. Architectural Overview

**ULTRON (Autonomous AI Procurement and Payment Agent)** is a modular, multi-agent procurement and transaction execution platform built with a **Python FastAPI** backend, **MySQL 8+** relational persistence layer (with automatic SQLAlchemy ORM + local JSON resilience), **OpenRouter / Groq LLM** reasoning, **Channel3** product discovery, and **PayPal Sandbox REST v2** payment execution.

```
+-----------------------------------------------------------------------------------+
|                        FRONTEND: Single-File SPA (index.html)                     |
|  Dashboard | Command Centre | Mission Control | Discovery | Cart | Plans | Orders |
+-----------------------------------------+-----------------------------------------+
                                          | REST JSON API (/api/*)
                                          v
+-----------------------------------------------------------------------------------+
|                        BACKEND: Python 3.10+ FastAPI (backend/)                   |
|  main.py  |  config.py  |  database.py  |  models.py  |  schemas.py               |
+-----------------------------------------+-----------------------------------------+
          |                               |                               |
          v                               v                               v
+-------------------+           +-------------------+           +-------------------+
|  MULTI-AGENT CORE |           |  DOMAIN SERVICES  |           |   INTEGRATIONS    |
|  (backend/agents) |           | (backend/services)|           |(backend/integrat.)|
| - planner.py      |           | - procurement_svc |           | - openrouter.py   |
| - researcher.py   |           | - execution_svc   |           | - paypal.py       |
| - procurement_agt |           | - approval_svc    |           | - channel3.py     |
| - payment_agent   |           +---------+---------+           +---------+---------+
+---------+---------+                     |                               |
          |                               v                               |
          +-------------------->+-------------------+                     |
                                |   MySQL 8+ DB     |                     |
                                | (11 Core Tables)  |                     |
                                +-------------------+                     |
                                                                          v
                                                    +-------------------------------+
                                                    | External Cloud APIs:          |
                                                    | - OpenRouter / Groq LLM API   |
                                                    | - PayPal Sandbox REST v2 API  |
                                                    | - Channel3 Product Catalog API|
                                                    +-------------------------------+
```

---

## 2. 13-Stage Autonomous Procurement Pipeline

1. **Natural Language Objective Parsing (`backend/agents/planner.py`)**:
   - Extracts category, budget ceiling, currency (`USD`, `INR`, `EUR`, `GBP`), target quantity, RAM/storage/VRAM/refresh-rate specs, and direct SKU/Product ID lookups.
   - Uses deterministic Python parsing first for speed and accuracy, augmented by OpenRouter/Groq structured LLM reasoning.
2. **Dynamic Mission Planning (`backend/services/execution_service.py`)**:
   - Creates an `Objective`, `Constraints`, and a multi-stage `Mission` execution graph.
3. **Product Discovery (`backend/agents/researcher.py` & `backend/integrations/channel3.py`)**:
   - Queries Channel3 API (when `CHANNEL3_API_KEY` is configured) and verified enterprise catalog snapshots.
4. **Constraint Filtering & Spec Evaluation (`backend/agents/procurement_agent.py`)**:
   - Verifies hard budget limits, stock availability, and technical specifications (RAM, SSD, VRAM, Hz, warranty).
5. **Multi-Criteria Ranking & Comparison**:
   - Ranks candidate products by price efficiency, specification match, vendor rating, and stock readiness.
6. **Versioned Purchase Plan Generation (`backend/services/procurement_service.py`)**:
   - Formulates a versioned `PurchasePlan` (`PLAN-PROC-...`) and line items (`PlanItem`).
7. **Human Governance Checkpoint (`backend/services/approval_service.py`)**:
   - Generates a formal `Approval` record (`APPR-PROC-...`) requiring explicit approval before any payment order can be created.
8. **PayPal Sandbox Order Creation (`backend/agents/payment_agent.py` & `backend/integrations/paypal.py`)**:
   - Authenticates with `https://api-m.sandbox.paypal.com/v1/oauth2/token` using `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`.
   - Creates a genuine PayPal Sandbox order via `POST /v2/checkout/orders` with `intent: "CAPTURE"`, merchant payee verification, and return/cancel callbacks.
9. **Buyer Approval & Automatic Backend Capture**:
   - Redirects the Personal Sandbox Buyer (`demo@example.invalid`) to the genuine PayPal `rel="approve"` link (`https://www.sandbox.paypal.com/checkoutnow?token=...`).
   - Upon return to `/api/payments/callback/return`, verifies `APPROVED` status via `GET /v2/checkout/orders/{id}` and captures funds once via `POST /v2/checkout/orders/{id}/capture`.
10. **Order Lifecycle, Tracking & Refund Governance (`backend/routes/orders.py`)**:
    - Tracks post-payment fulfillment, carrier tracking numbers, and executes verified PayPal Sandbox refunds (`POST /v2/payments/captures/{capture_id}/refund`) if a captured order is cancelled.

---

## 3. Database Layer & Resilience (`backend/database.py` & `backend/models.py`)

- **Primary Engine**: MySQL 8+ via SQLAlchemy (`mysql+pymysql://...`) matching `database/schema.sql`.
- **Safe Startup & Zero-Crash Fallback**: If MySQL is not yet running locally when the user first launches `run.bat`, ULTRON logs a clear diagnostic notice and seamlessly synchronizes state with `data/ultron_db.json` so the dashboard and all APIs start immediately without crashing.

---

## 4. Security Architecture

- **Zero Browser Secrets**: `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `PAYPAL_CLIENT_SECRET`, and `CHANNEL3_API_KEY` are read exclusively by `backend/config.py` from `.env` and are never exposed to `index.html` or API responses.
- **Server-Side Payment Verification**: No order is marked `COMPLETED` based on a frontend redirect alone. Every status transition (`ORDER CREATED` → `WAITING FOR BUYER APPROVAL` → `BUYER APPROVED` → `CAPTURE IN PROGRESS` → `PAYMENT COMPLETED`) is verified against `https://api-m.sandbox.paypal.com`.
- **Idempotency & Protected Records**: Completed PayPal captures cannot be captured a second time, and genuine historical PayPal Sandbox records (`REDACTED_TEST_REFERENCE`, `REDACTED_TEST_REFERENCE`, `REDACTED_TEST_REFERENCE`) are permanently protected from test data cleanup.
