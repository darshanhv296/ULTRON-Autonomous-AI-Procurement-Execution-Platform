# ⚡ ULTRON — Autonomous AI Procurement & Payment Execution Platform










**ULTRON** (`v4.8.0`) is a FastAPI-powered multi-agent procurement and transaction execution prototype featuring natural-language objective parsing, product discovery, human-in-the-loop approval governance, local JSON persistence with MySQL 8+ schema initialization, and PayPal Developer Sandbox REST v2 checkout.

---

## 1. Project Overview

ULTRON bridges AI-assisted procurement planning with structured human governance. A single-file web interface (`index.html`) communicates over REST JSON APIs with a modular Python FastAPI backend (`backend/`), where specialized agents parse procurement requests, discover and rank candidate products, generate versioned purchase plans, enforce an explicit approval checkpoint, and execute checkout through PayPal Developer Sandbox REST v2.

---

## 2. Problem Statement

Procurement workflows and AI-driven purchasing face two opposing challenges:

1. **Manual Procurement Is Fragmented**: Turning a plain-English request (*"Buy a 144Hz monitor under $200"*) into structured requirements, vendor comparisons, budget checks, approval records, and payment tracking normally requires switching across multiple tools.
2. **Unchecked AI Agents Are Unsafe With Payments**: Allowing an LLM to trigger payment APIs directly risks hallucinated items, budget overruns, or unapproved charges.

---

## 3. Solution

ULTRON separates **autonomous AI research and planning** from **financial execution**:

* **Deterministic + LLM Parsing**: Extracts currency, budget limits, quantities, and technical specs using deterministic Python rules first, augmented by Groq or OpenRouter LLM reasoning when configured.
* **Constraint-Checked Ranking**: Filters candidate products against hard budget and specification constraints before recommending a purchase plan.
* **Mandatory Human Approval Gate**: Every purchase plan (`PLAN-PROC-...`) generates a pending approval record (`APPR-PROC-...`). PayPal Sandbox order creation is blocked until that plan is explicitly approved.
* **Server-Side Sandbox Verification**: PayPal order creation, buyer return verification, and capture are executed on the server against `https://api-m.sandbox.paypal.com`.

---

## 4. Key Features

* **Single-File Web Interface (`index.html`)**: Served directly by FastAPI at `/` with Dashboard, Command Centre, Mission Control, Discovery, Cart, Plans, and Orders views.
* **Multi-Agent Core (`backend/agents/`)**: Four dedicated agents (`Planner`, `Researcher`, `Procurement`, and `Payment`) coordinated by domain services.
* **Optional AI Providers (`backend/integrations/openrouter.py`)**: Supports **Groq** and **OpenRouter** with automatic fallback to deterministic Python parsing when no API keys are configured.
* **Product Discovery (`backend/integrations/channel3.py`)**: Queries the Channel3 API when `CHANNEL3_API_KEY` is configured and merges results with built-in catalog snapshots.
* **PayPal Sandbox REST v2 (`backend/integrations/paypal.py`)**: Implements OAuth2 `client_credentials` token exchange, merchant credential verification, order creation (`intent: "CAPTURE"`), return callback verification, and duplicate-capture prevention.
* **Zero-Crash Startup (`backend/database.py`)**: Initializes cleanly using local JSON persistence (`data/ultron_db.json`) even when MySQL is not running.

---

## 5. Feature Implementation Status

The table below reflects the verified state of the source code in this release:

| Feature | Status | Implementation Notes |
| :--- | :--- | :--- |
| FastAPI SPA Serving (`/`) & OpenAPI (`/docs`) | **Implemented** | `backend/main.py` serves `index.html` at `/` and Swagger UI at `/docs`. |
| Natural-Language Objective & Spec Parsing | **Implemented** | Deterministic Python parser + optional Groq/OpenRouter in `backend/agents/planner.py`. |
| Product Catalog Snapshots & Comparison | **Implemented** | Built-in enterprise hardware snapshots + comparison scoring in `procurement_service.py`. |
| Channel3 Live Product Discovery | **Implemented (Optional)** | Calls `CHANNEL3_API_URL` when `CHANNEL3_API_KEY` is set; falls back to snapshots otherwise. |
| Purchase Plan & Human Approval Gate | **Implemented** | `backend/services/approval_service.py` enforces `APPROVED` state before PayPal order creation. |
| PayPal Sandbox Order Create, Verify & Capture | **Implemented (Sandbox Only)** | Real HTTP calls to `https://api-m.sandbox.paypal.com` in `backend/integrations/paypal.py`. |
| Local JSON Persistence (`data/ultron_db.json`) | **Implemented (Active Store)** | All runtime reads/writes persist to `data/ultron_db.json` and `data/ultron_buyer_settings.json`. |
| MySQL 8+ Connection & Table Initialization | **Partially Implemented** | `_init_mysql_engine()` connects and runs `Base.metadata.create_all()`, but runtime CRUD reads/writes still use JSON (`self.state` / `ultron_db.json`). |
| Order Carrier Tracking (`POST /api/orders/{id}/refresh-tracking`) | **Simulated** | Generates local `FedEx Ground Delivery` / `FX-TRK-...` metadata without an external carrier API. |
| Order Cancellation & Refund (`POST /api/orders/{id}/cancel`) | **Simulated (Local State)** | Updates local status to `REFUNDED` or `CANCELLED`; does **not** call PayPal's `/v2/payments/captures/{id}/refund` API. |
| Route-Level Authentication & RBAC | **Not Implemented** | API routes have no login, JWT, or session authentication middleware in this release. |
| Frontend-Backend Route Parity | **Partial Mismatch** | 7 `/api/*` paths referenced in `index.html` do not match registered backend routes (see Section 26). |

---

## 6. Complete Procurement Workflow

### End-to-End Flow in Code

1. **Procurement Request Submission**: User submits a prompt via the UI or `POST /api/procurement/natural-language` (or creates a structured objective via `POST /api/objectives`).
2. **Natural-Language Interpretation (`planner.py`)**: Extracts category, budget ceiling, currency (`USD`, `INR`, `EUR`, `GBP`), quantity, and required specs.
3. **Requirement & Constraint Extraction (`procurement_service.py`)**: Persists an `Objective` and hard `Constraints` (`max_budget`, `quality_tier`).
4. **Product Research & Discovery (`researcher.py`)**: Queries Channel3 (if configured) and local `product_snapshots`.
5. **Budget & Specification Evaluation (`procurement_agent.py`)**: Filters candidates against budget and stock constraints and scores them.
6. **Product Comparison**: Ranks candidates and selects a top recommendation (also exposed via `POST /api/products/compare`).
7. **Procurement Plan Generation**: Creates a versioned `PurchasePlan` (`PLAN-PROC-...`) with itemized `PlanItem` records.
8. **Human Approval (`approval_service.py`)**: Generates a `PENDING` `Approval` (`APPR-PROC-...`). A reviewer approves or rejects via `POST /api/approvals/{approval_id}/decide`.
9. **PayPal Sandbox Order Creation (`payment_agent.py` & `paypal.py`)**: After approval, `POST /api/payments/create` calls PayPal Sandbox `POST /v2/checkout/orders` (`intent: "CAPTURE"`).
10. **Buyer Approval & Checkout**: User opens the returned `checkout_url` (`https://www.sandbox.paypal.com/checkoutnow?token=...`) and logs in with a Sandbox Personal buyer account.
11. **Payment Verification & Capture**: PayPal redirects to `GET /api/payments/callback/return`, which verifies `APPROVED` status via `GET /v2/checkout/orders/{id}` and captures funds via `POST /v2/checkout/orders/{id}/capture`.
12. **Order State Updates**: Marks the payment `COMPLETED` (with `capture_id`), updates the plan to `PAID`, and marks the objective `COMPLETED`.
13. **Tracking & Audit Records**: Logs `objective_events` in local state; `refresh-tracking` attaches simulated shipping metadata.

> **Pipeline Stage Note**: `procurement_service.py` returns an 8-stage execution summary (`Understand Objective` → `Human Approval Checkpoint`) during natural-language pipeline execution, while `missions` track completion up to stage `13. Lifecycle Settlement & Verification` after payment capture.

---

## 7. AI Agent Architecture

| Agent | File | Responsibilities |
| :--- | :--- | :--- |
| **Planner Agent** | `backend/agents/planner.py` | Parses natural-language requests into structured category, budget, currency, quantity, and spec constraints using deterministic rules + optional Groq/OpenRouter. |
| **Researcher Agent** | `backend/agents/researcher.py` | Searches Channel3 (when configured) and built-in `product_snapshots` to gather candidate products. |
| **Procurement Agent** | `backend/agents/procurement_agent.py` | Evaluates candidates against budget/spec constraints, computes match scores, and ranks recommendations. |
| **Payment Agent** | `backend/agents/payment_agent.py` | Coordinates payment readiness checks, delegates PayPal Sandbox order creation, and syncs settlement status. |

---

## 8. System Architecture

FastAPI (`backend/main.py`) serves both the frontend (`index.html` at `/`) and all REST API endpoints (`/api/*`) from a single local process—no separate Node.js or frontend dev server is required.

```text
Browser
  │
  ▼ (HTTP GET /)
index.html (Single-File HTML / CSS / JavaScript SPA)
  │
  ▼ (REST JSON /api/*)
FastAPI Application (backend/main.py)
  │
  ├──▶ API Routers (backend/routes/: procurement, products, agents, orders, payments)
  │       │
  │       ├──▶ Domain Services (backend/services/: procurement, execution, approval)
  │       │       └──▶ Multi-Agent Core (backend/agents/: planner, researcher, procurement, payment)
  │       │
  │       └──▶ External Integrations (backend/integrations/: openrouter, channel3, paypal)
  │
  └──▶ Persistence (backend/database.py + backend/models.py)
          ├── Active Runtime Store: data/ultron_db.json & data/ultron_buyer_settings.json
          └── MySQL 8+ Engine (optional connection + schema init via Base.metadata.create_all)
```

---

## 9. Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript (single-file `index.html`) |
| **Backend** | Python 3.10+, FastAPI (`>=0.110.0`), Uvicorn (`>=0.29.0`), Pydantic v2 (`>=2.7.0`) |
| **ORM / Database** | SQLAlchemy (`>=2.0.30`), PyMySQL (`>=1.1.0`), Cryptography (`>=42.0.0`), MySQL 8.0+ |
| **HTTP & Env** | HTTPX (`>=0.27.0`), Requests (`>=2.31.0`), python-dotenv (`>=1.0.1`), python-multipart |
| **External APIs** | OpenRouter / Groq (LLM), Channel3 (Product Discovery), PayPal Sandbox REST v2 |

---

## 10. Project Directory Structure

```text
ULTRON/
├── index.html                          # Single-file SPA served at /
├── requirements.txt                    # Python package dependencies
├── .env                                # Safe environment variable template (no real secrets)
├── LICENSE                             # MIT License
├── run.bat                             # Windows 10/11 launcher script
├── run.sh                              # macOS/Linux launcher script
├── build_zip.py                        # Release packaging script
├── README.md                           # Project documentation
│
├── database/
│   └── schema.sql                      # MySQL 8+ DDL for 11 core tables
│
├── docs/
│   ├── ARCHITECTURE.md                 # System architecture notes
│   └── SETUP.md                        # Quick setup notes
│
└── backend/
    ├── __init__.py
    ├── main.py                         # FastAPI app, CORS, router registration, /api/health, /
    ├── config.py                       # Loads .env settings and validates non-placeholder credentials
    ├── database.py                     # JSON state manager + optional MySQL engine initialization
    ├── models.py                       # SQLAlchemy 2.0 ORM models (11 tables)
    ├── schemas.py                      # Pydantic v2 request/response models
    ├── agents/
    │   ├── __init__.py
    │   ├── planner.py
    │   ├── researcher.py
    │   ├── procurement_agent.py
    │   └── payment_agent.py
    ├── services/
    │   ├── __init__.py
    │   ├── procurement_service.py
    │   ├── execution_service.py
    │   └── approval_service.py
    ├── integrations/
    │   ├── __init__.py
    │   ├── openrouter.py
    │   ├── channel3.py
    │   └── paypal.py
    └── routes/
        ├── __init__.py
        ├── procurement.py
        ├── products.py
        ├── agents.py
        ├── orders.py
        └── payments.py
```

---

## 11. System Requirements

* **Operating System**: Windows 10/11, macOS, or Linux
* **Python**: 3.10 or newer
* **MySQL**: 8.0+ *(optional; application starts in local JSON mode without MySQL)*
* **Node.js / npm**: **Not required** (FastAPI serves `index.html` directly)

---

## 12. Windows Installation (Windows 10/11)

1. Open the extracted `ULTRON` project root folder in File Explorer, click the address bar, type `cmd`, and press **Enter** to open Command Prompt in the project root.
2. Run the following commands in order:

```cmd
python --version
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

3. Open the application in your browser:
   * **Frontend Dashboard**: `http://127.0.0.1:8000`
   * **Interactive API Docs (Swagger)**: `http://127.0.0.1:8000/docs`
   * **Health Check**: `http://127.0.0.1:8000/api/health`
4. To stop the server, press `Ctrl + C` in the Command Prompt window.

*(Alternatively, double-click `run.bat` for automated first-time setup and launch.)*

### Quick Restart (Windows)

```cmd
venv\Scripts\activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

---

## 13. macOS / Linux Installation

1. Open a terminal in the `ULTRON` project root and run:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

2. Open `http://127.0.0.1:8000` (Frontend) or `http://127.0.0.1:8000/docs` (API Docs). Press `Ctrl + C` to stop.

### Quick Restart (macOS / Linux)

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

---

## 14. Environment Configuration

Copy `.env.example` to `.env`. Every variable below is read by `backend/config.py`. The application **can start without any external API keys**.

| Variable | Required | Default / Safe Example | Description & Impact When Absent |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | Optional | `ULTRON` | Display name returned by `/api/health`. |
| `APP_ENV` | Optional | `development` | Runtime environment label. |
| `APP_HOST` | Optional | `127.0.0.1` | Host interface for Uvicorn (`__main__` mode). |
| `APP_PORT` | Optional | `8000` | Port for Uvicorn (`__main__` mode; also reads `PORT`). |
| `APP_URL` | Optional | `http://127.0.0.1:8000` | Base application URL. |
| `MYSQL_HOST` | Optional | `localhost` | MySQL server hostname. App uses JSON mode if unreachable. |
| `MYSQL_PORT` | Optional | `3306` | MySQL server port. |
| `MYSQL_DATABASE` | Optional | `ultron` | MySQL database/schema name. |
| `MYSQL_USER` | Optional | `root` | MySQL username. |
| `MYSQL_PASSWORD` | Optional | `CHANGE_ME` | MySQL password. If `CHANGE_ME` or empty, MySQL connection is skipped. |
| `OPENROUTER_API_KEY` | Optional | `YOUR_KEY` | OpenRouter API key. Without it (and Groq), planner uses deterministic Python parsing. |
| `OPENROUTER_MODEL` | Optional | `meta-llama/llama-3.3-70b-instruct` | OpenRouter model ID. |
| `GROQ_API_KEY` | Optional | `YOUR_OPTIONAL_GROQ_KEY` | Groq API key (checked before OpenRouter in `openrouter.py`). |
| `GROQ_MODEL` | Optional | `llama-3.3-70b-versatile` | Groq model ID (read in `config.py`, optional in `.env`). |
| `PAYPAL_CLIENT_ID` | Optional | `YOUR_SANDBOX_CLIENT_ID` | PayPal Developer Sandbox Client ID. Without it, Sandbox order creation/capture fails with a config error. |
| `PAYPAL_CLIENT_SECRET` | Optional | `YOUR_SANDBOX_SECRET` | PayPal Developer Sandbox Secret. |
| `PAYPAL_BASE_URL` | Optional | `https://api-m.sandbox.paypal.com` | PayPal Sandbox REST API base URL. |
| `PAYPAL_MERCHANT_EMAIL` | Optional | *(empty)* | Sandbox Business/Merchant email used as `payee.email_address`. |
| `PAYPAL_BUYER_EMAIL` | Optional | *(empty)* | Sandbox Personal buyer email stored in buyer config for testing. |
| `CHANNEL3_API_KEY` | Optional | `YOUR_KEY` | Channel3 Product Discovery key. Without it, discovery uses built-in catalog snapshots. |
| `CHANNEL3_API_URL` | Optional | `https://api.channel3.io/v1` | Channel3 API base URL. |

---

## 15. OpenRouter & Other AI Provider Configuration

`backend/integrations/openrouter.py` supports two cloud LLM providers plus a local deterministic fallback:

* **Groq** (`GROQ_API_KEY`, `GROQ_MODEL`): Checked first when `GROQ_API_KEY` is configured (`https://api.groq.com/openai/v1/chat/completions`).
* **OpenRouter** (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`): Used when Groq is not configured or as a fallback (`https://openrouter.ai/api/v1/chat/completions`). Obtain a key from [OpenRouter](https://openrouter.ai/).
* **Deterministic Python Fallback**: If neither key is set, `planner.py` parses budgets, currencies, quantities, and specs locally without external API calls.

---

## 16. Channel3 Configuration

Obtain an API key from Channel3 if you have access and set `CHANNEL3_API_KEY` and `CHANNEL3_API_URL` in `.env`. When unconfigured, `backend/integrations/channel3.py` serves results from the built-in hardware catalog snapshots in `backend/database.py`.

---

## 17. PayPal Sandbox Setup

ULTRON is configured **exclusively for PayPal Developer Sandbox testing** in this release.

1. Sign in to the [PayPal Developer Dashboard](https://developer.paypal.com/) and open **Apps & Credentials**.
2. Ensure the environment toggle is set to **Sandbox**.
3. Click **Create App**, choose **Merchant**, and copy the **Client ID** and **Secret**.
4. Open **Testing Tools → Sandbox Accounts** and note one **Business (Merchant)** email and one **Personal (Buyer)** email.
5. Add them to `.env`:
   ```env
   PAYPAL_CLIENT_ID=your_sandbox_client_id
   PAYPAL_CLIENT_SECRET=your_sandbox_secret
   PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
   PAYPAL_MERCHANT_EMAIL=your-sandbox-business@business.example.com
   PAYPAL_BUYER_EMAIL=your-sandbox-personal@personal.example.com
   ```
6. **Checkout & Verification Behavior (`backend/integrations/paypal.py`)**:
   * **Order Creation**: `create_sandbox_order()` requires the plan's approval record to be `APPROVED`, reuses an existing `CREATED`/`APPROVED`/`PAYER_ACTION_REQUIRED` order for the same `plan_id` to prevent duplicates, and calls `POST /v2/checkout/orders` with `intent: "CAPTURE"`.
   * **Buyer Approval**: Redirects the user to PayPal's `rel="approve"` link (`https://www.sandbox.paypal.com/checkoutnow?token=...`).
   * **Server-Side Verification & Capture**: `GET /api/payments/callback/return` calls `verify_and_sync_order()` (`GET /v2/checkout/orders/{id}`) and `capture_sandbox_order()` (`POST /v2/checkout/orders/{id}/capture`) using a `PayPal-Request-Id` idempotency header and checks `DUPLICATE_CAPTURE_PREVENTED` if already `COMPLETED`.
   * **Payment Record Handling**: Local payment status is synchronized to `data/ultron_db.json`; a local status alone never proves a real financial transaction.

> **Important Security Disclaimer**: This release does **not** support or include instructions for live production payments. Moving to live payments requires a separate security review, route-level authentication/authorization, CSRF protection, rate limiting, PayPal webhook signature verification, and full amount/currency reconciliation safeguards.

---

## 18. MySQL Setup & Local JSON Persistence

* **MySQL Configuration**: Create a database named `ultron` in MySQL 8+ and optionally run `database/schema.sql` (11 tables: `users`, `objectives`, `constraints`, `missions`, `product_snapshots`, `plans`, `plan_items`, `approvals`, `payment_orders`, `ai_runs`, `objective_events`).
* **Auto-Creation Behavior**: When `MYSQL_PASSWORD` is set (and not `CHANGE_ME`), `backend/database.py` connects via SQLAlchemy and runs `Base.metadata.create_all(bind=self.engine)` to create tables automatically if missing.
* **Authoritative Runtime Store**: Currently, `DatabaseManager` uses `self.SessionLocal` only during initialization; **all runtime CRUD operations read from and write to `data/ultron_db.json` and `data/ultron_buyer_settings.json`**. MySQL is not yet the authoritative read/write store for workflow state.

---

## 19. How to Use ULTRON

1. Start the server and open `http://127.0.0.1:8000`.
2. Check system & PayPal Sandbox readiness via `/api/health` or the dashboard status panel.
3. Submit a natural-language procurement request (e.g., *"Buy a 144Hz gaming monitor under $200"*).
4. Review the ranked candidates and generated **Purchase Plan** (`PLAN-PROC-...`).
5. Open **Approvals** and approve the pending checkpoint (`APPR-PROC-...`).
6. Create a **PayPal Sandbox Order**, complete buyer login on PayPal Sandbox, and verify the automatic return capture.

---

## 20. Complete API Reference

All endpoints below were verified directly from `backend/main.py` and `backend/routes/*.py`. **Authentication is not implemented** on these routes in this release.

### System & Export (`backend/main.py`)
| Method | Endpoint | Purpose | Parameters / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves `index.html` frontend | None |
| `GET` | `/docs` | Interactive Swagger UI | None |
| `GET` | `/api/health` | System, DB, AI, and PayPal status | None |
| `GET` | `/ULTRON_GITHUB_READY.zip` | Download release ZIP | None |
| `GET` | `/api/export/github-zip` | Download/build release ZIP | None |

### Procurement & Governance (`backend/routes/procurement.py`)
| Method | Endpoint | Purpose | Parameters / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/dashboard/metrics` | Dashboard KPI summary | None |
| `GET` | `/api/objectives` | List objectives | None |
| `GET` | `/api/objectives/{objective_id}` | Get single objective | Path: `objective_id` |
| `POST` | `/api/objectives` | Create objective | JSON: `CreateObjectiveRequest` |
| `POST` | `/api/objectives/{objective_id}/execute` | Execute mission for objective | Path: `objective_id` |
| `POST` | `/api/procurement/natural-language` | Run NL procurement pipeline | JSON: `NaturalLanguageProcurementRequest` |
| `GET` | `/api/plans` | List purchase plans | None |
| `GET` | `/api/plans/{plan_id}` | Get single plan | Path: `plan_id` |
| `POST` | `/api/plans` | Create purchase plan | JSON: `CreatePlanRequest` |
| `GET` | `/api/approvals` | List approval records | None |
| `POST` | `/api/approvals/{approval_id}/decide` | Approve or reject plan | Path: `approval_id`; JSON: `ApprovalDecisionRequest` |
| `GET` | `/api/audit/events` | List audit events (alias: `/api/audit-events`) | Query: `objective_id` (optional) |
| `GET` | `/api/notifications` | Recent event notifications | None |
| `GET` | `/api/search` | Search objectives, products, plans, payments | Query: `q` |

### Products & Cart (`backend/routes/products.py`)
| Method | Endpoint | Purpose | Parameters / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/products/search` | Search Channel3 / snapshots | Query: `q`, `category`, `max_price` |
| `GET` | `/api/products/snapshots` | List product snapshots | None |
| `POST` | `/api/products/compare` | Compare products | JSON: `ProductCompareRequest` |
| `GET` | `/api/cart` | Get cart & totals | None |
| `POST` | `/api/cart/items` | Add item to cart | JSON: `CartItemAddRequest` |
| `PATCH` / `PUT` | `/api/cart/items/{product_id}` | Update cart item quantity | Path: `product_id`; JSON: `CartItemQuantityRequest` |
| `DELETE` | `/api/cart/items/{product_id}` | Remove item from cart | Path: `product_id` |
| `DELETE` | `/api/cart` | Clear cart | None |
| `POST` | `/api/cart/checkout` | Convert cart into plan + approval | JSON: `CartCheckoutRequest` |

### Agents & Missions (`backend/routes/agents.py`)
| Method | Endpoint | Purpose | Parameters / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/missions` | List agent missions | None |
| `POST` | `/api/missions/{mission_id}/replan` | Replan mission | Path: `mission_id` |
| `GET` | `/api/ai/runs` | List AI run logs (alias: `/api/ai-runs`) | None |
| `POST` | `/api/ai/assistant` | Query AI assistant (alias: `/api/assistant/query`) | JSON: `AssistantQueryRequest` |

### Orders (`backend/routes/orders.py`)
| Method | Endpoint | Purpose | Parameters / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/orders` | List orders | None |
| `GET` | `/api/orders/{order_id}` | Get order details | Path: `order_id` |
| `POST` | `/api/orders/{order_id}/refresh-tracking` | Generate/update simulated tracking | Path: `order_id` |
| `POST` | `/api/orders/{order_id}/cancel` | Cancel order locally | Path: `order_id`; JSON: `CancelOrderRequest` |

### PayPal Sandbox Payments (`backend/routes/payments.py`)
| Method | Endpoint | Purpose | Parameters / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/payments` | List payment orders | None |
| `GET` | `/api/payments/{payment_id}` | Get payment order | Path: `payment_id` |
| `POST` | `/api/payments/create` | Create PayPal Sandbox order | JSON: `CreatePaymentRequest` |
| `GET` | `/api/payments/callback/return` | PayPal return callback (verify & capture) | Query: `token`, `PayerID` |
| `GET` | `/api/payments/callback/cancel` | PayPal cancel callback | Query: `token` |
| `POST` | `/api/payments/{payment_id}/verify-paypal` | Verify order against PayPal Sandbox | Path: `payment_id` |
| `POST` | `/api/payments/{payment_id}/auto-capture` | Verify & capture order | Path: `payment_id`; JSON: `AutoCaptureRequest` |
| `POST` | `/api/payments/{payment_id}/approve` | Sync approval status from PayPal | Path: `payment_id`; JSON: `ApprovePaymentRequest` |
| `POST` | `/api/payments/{payment_id}/capture` | Capture approved PayPal order | Path: `payment_id` |
| `GET` | `/api/payments/{payment_id}/refund-eligibility` | Check local refund eligibility | Path: `payment_id` |
| `GET` | `/api/payments/cleanup-test-records/preview` | Preview test cleanup (alias: `/api/admin/...`) | None |
| `POST` | `/api/payments/cleanup-test-records` | Execute test cleanup (alias: `/api/admin/...`) | JSON: `CleanupTestRecordsRequest` |
| `GET` | `/api/paypal/merchant-verification` | Check Sandbox merchant OAuth status | None |
| `POST` | `/api/paypal/merchant-verification/reload` | Reload `.env` & re-verify OAuth | None |
| `GET` / `POST` | `/api/paypal/buyer-config` | Get or save Sandbox buyer email | JSON: `BuyerConfigRequest` (POST) |
| `POST` | `/api/paypal/buyer-config/test` | Test Sandbox buyer/merchant separation | JSON: `BuyerConfigRequest` |

---

## 21. Troubleshooting

* **`ModuleNotFoundError: No module named 'sqlalchemy'`**: Ensure your virtual environment is activated (`venv\Scripts\activate` or `source .venv/bin/activate`) and run `pip install -r requirements.txt`.
* **PayPal shows `PENDING CREDENTIAL SETUP`**: Verify `.env` exists in the project root and `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` do not use placeholder values starting with `YOUR_`.
* **MySQL shows standby/local mode**: Verify MySQL 8+ is running, database `ultron` exists, and `MYSQL_PASSWORD` in `.env` is not `CHANGE_ME`.

---

## 22. Security and Privacy

* `.gitignore` excludes `.env`, `.env.*`, `venv/`, `.venv/`, `data/`, `__pycache__/`, `*.py[cod]`, `*.log`, `*.sqlite3`, and `*.db`.
* No real API keys, passwords, buyer/merchant emails, or historical PayPal transaction IDs are hardcoded in the repository.
* Secrets (`OPENROUTER_API_KEY`, `GROQ_API_KEY`, `PAYPAL_CLIENT_SECRET`, `CHANNEL3_API_KEY`) are read only on the server via `backend/config.py`.
* **Honest Limitations**: No route authentication/authorization is implemented, `objective_events` is a mutable local list (not cryptographically immutable), and CORS is configured for local origins (`127.0.0.1:8000`, `localhost:8000`).

---

## 23. Limitations and Future Roadmap

* **Frontend-Backend Route Mismatches**: `index.html` references 7 paths not registered in `backend/routes/` (`/api/nlp/procure`, `/api/cart/clear`, `/api/orders/{id}/retailer-confirm`, `/api/plans/{id}/request-approval`, `/api/plans/generate`, `/api/products/discover`, `/api/products/lookup`). Aligning these handlers is a priority next step.
* **MySQL Write-Through**: Wire `DatabaseManager` CRUD methods to `self.SessionLocal` so MySQL becomes the primary read/write store.
* **Live PayPal Refund API**: Connect `POST /api/orders/{id}/cancel` to PayPal's `/v2/payments/captures/{capture_id}/refund` endpoint.
* **Authentication & Automated Test Suite**: Add JWT/session auth, RBAC for approvals, and a `pytest` integration suite.

---

## 24. Testing Instructions & Verified Results

To run syntax and startup verification locally after installing `requirements.txt`:

```bash
python -m compileall backend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Verified Audit Results (This Release)**:
* **Python Syntax Compilation (`py_compile`)**: Passed on all **26** `.py` files (`0` errors).
* **Route Inspection**: Verified **58** registered FastAPI routes across `backend/main.py` and `backend/routes/*.py`.
* **Sandbox Environment Note**: `sqlalchemy` and `pymysql` were not installed in the isolated audit sandbox, so live Uvicorn startup, `/`, `/docs`, `/api/health`, MySQL, PayPal, OpenRouter, and Channel3 external integration tests were **not** executed live during the audit.
