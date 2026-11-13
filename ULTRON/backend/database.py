"""
ULTRON Database & Persistence Layer
Supports MySQL 8+ via SQLAlchemy 2.0 ORM with automatic resilient local JSON synchronization
so the application starts safely even before MySQL is started locally.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.config import BASE_DIR, settings
from backend.models import Base

DATA_DIR = BASE_DIR / "data"
DB_JSON_FILE = DATA_DIR / "ultron_db.json"
BUYER_CONFIG_FILE = DATA_DIR / "ultron_buyer_settings.json"

PROTECTED_PAYMENT_ID = "REDACTED_TEST_REFERENCE"
PROTECTED_PAYPAL_ORDER_ID = "REDACTED_TEST_REFERENCE"
PROTECTED_CAPTURE_ID = "REDACTED_TEST_REFERENCE"
UNVERIFIED_PAYMENT_REF = "REDACTED_TEST_REFERENCE"

ULTRON_MERCHANT = {
    "merchant_id": "ULTRON-ENT-SANDBOX-01",
    "merchant_name": "ULTRON Autonomous Procurement Corp.",
    "merchant_email": settings.PAYPAL_MERCHANT_EMAIL or "demo@example.invalid",
    "sandbox_url": "https://sandbox.paypal.com",
    "api_base_url": settings.PAYPAL_BASE_URL or "https://api-m.sandbox.paypal.com",
    "environment": "SANDBOX",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class DatabaseManager:
    """Manages MySQL 8+ SQLAlchemy connection + resilient local persistence."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.mysql_connected: bool = False
        self.mysql_status_message: str = "MySQL 8+ (Local Resilient Sync Mode)"
        self.engine = None
        self.SessionLocal = None
        self._init_mysql_engine()
        self.state: Dict[str, Any] = self._load_state()

    def _init_mysql_engine(self) -> None:
        try:
            if settings.MYSQL_PASSWORD and settings.MYSQL_PASSWORD != "CHANGE_ME":
                self.engine = create_engine(
                    settings.mysql_url,
                    pool_pre_ping=True,
                    connect_args={"connect_timeout": 3},
                )
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                Base.metadata.create_all(bind=self.engine)
                self.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )
                self.mysql_connected = True
                self.mysql_status_message = (
                    f"MySQL 8+ Connected ({settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE})"
                )
        except Exception as exc:
            self.mysql_connected = False
            self.mysql_status_message = (
                f"ultron_db Active (Local Persistence Mode — MySQL {settings.MYSQL_HOST}:{settings.MYSQL_PORT} standby: {str(exc)[:60]})"
            )

    def _default_seed_state(self) -> Dict[str, Any]:
        now = _utc_now_iso()
        return {
            "users": [
                {
                    "id": "usr-admin-01",
                    "name": "Demo Administrator",
                    "email": "demo@example.invalid",
                    "role": "CHIEF_PROCUREMENT_ARCHITECT",
                    "created_at": "2026-11-11T15:00:00.000Z",
                }
            ],
            "objectives": [
                {
                    "id": "OBJ-46733",
                    "user_id": "usr-admin-01",
                    "title": "Procure MONITOR: Purchase a monitor with a minimum 144Hz refresh rate.",
                    "description": "Purchase a monitor with a minimum 144Hz refresh rate.",
                    "status": "COMPLETED",
                    "budget_limit": None,
                    "currency": "USD",
                    "created_at": "2026-11-12T18:49:25.000Z",
                    "updated_at": "2026-11-12T19:19:29.184Z",
                },
                {
                    "id": "OBJ-1001",
                    "user_id": "usr-admin-01",
                    "title": "Procure Enterprise AI Dev Workstation Peripherals & Monitors",
                    "description": "Autonomous sourcing of dual color-calibrated 4K HDR displays and ergonomic peripherals within $1,000 budget.",
                    "status": "COMPLETED",
                    "budget_limit": 1000.0,
                    "currency": "USD",
                    "created_at": "2026-11-11T15:34:05.623Z",
                    "updated_at": "2026-11-12T14:34:05.623Z",
                },
                {
                    "id": "OBJ-1002",
                    "user_id": "usr-admin-01",
                    "title": "Autonomous GPU Node Sourcing for Local LLM Cluster",
                    "description": "Source 2x high-memory compute accelerators with enterprise PCIe compatibility, target under $1,800 total.",
                    "status": "AWAITING_APPROVAL",
                    "budget_limit": 1800.0,
                    "currency": "USD",
                    "created_at": "2026-11-12T14:34:05.623Z",
                    "updated_at": "2026-11-12T15:34:05.622Z",
                },
            ],
            "constraints": [
                {
                    "id": "CST-101",
                    "objective_id": "OBJ-1001",
                    "constraint_type": "max_budget",
                    "constraint_value": "1000.00 USD",
                    "is_hard_constraint": True,
                    "created_at": "2026-11-11T15:34:05.623Z",
                },
                {
                    "id": "CST-201",
                    "objective_id": "OBJ-1002",
                    "constraint_type": "max_budget",
                    "constraint_value": "1800.00 USD",
                    "is_hard_constraint": True,
                    "created_at": "2026-11-12T14:34:05.623Z",
                },
            ],
            "missions": [
                {
                    "id": "MSN-46733",
                    "objective_id": "OBJ-46733",
                    "status": "COMPLETED",
                    "current_stage": "13. Lifecycle Settlement & Verification",
                    "agent_assigned": "ULTRON Payment & Settlement Agent",
                    "started_at": "2026-11-12T18:49:25.000Z",
                    "completed_at": "2026-11-12T19:19:29.184Z",
                },
                {
                    "id": "MSN-1001",
                    "objective_id": "OBJ-1001",
                    "status": "COMPLETED",
                    "current_stage": "13. Lifecycle Settlement & Verification",
                    "agent_assigned": "ULTRON Payment & Settlement Agent",
                    "started_at": "2026-11-11T15:34:05.623Z",
                    "completed_at": "2026-11-12T14:34:05.623Z",
                },
            ],
            "product_snapshots": self._default_product_catalog(),
            "plans": [
                {
                    "id": "PLAN-PROC-7893",
                    "objective_id": "OBJ-46733",
                    "version": 1,
                    "status": "PAID",
                    "total_amount": 129.99,
                    "currency": "USD",
                    "notes": 'Autonomous selection: 1x ASUS TUF Gaming VG249Q1A 23.8" FHD 165Hz (144Hz+ Supported) IPS 1ms Gaming Monitor ($129.99 USD).',
                    "created_at": "2026-11-12T18:49:26.000Z",
                    "updated_at": "2026-11-12T19:19:29.184Z",
                },
                {
                    "id": "PLAN-PROC-001",
                    "objective_id": "OBJ-1001",
                    "version": 1,
                    "status": "PAID",
                    "total_amount": 899.79,
                    "currency": "USD",
                    "notes": "Verified Enterprise Workstation Display & Dock Bundle ($899.79 USD).",
                    "created_at": "2026-11-11T15:34:05.623Z",
                    "updated_at": "2026-11-12T14:34:05.623Z",
                },
                {
                    "id": "PLAN-PROC-002",
                    "objective_id": "OBJ-1002",
                    "version": 1,
                    "status": "APPROVED",
                    "total_amount": 79.99,
                    "currency": "USD",
                    "notes": "Keychron K8 Pro QMK/VIA Wireless Mechanical Keyboard ($79.99 USD).",
                    "created_at": "2026-11-12T14:34:05.623Z",
                    "updated_at": "2026-11-12T15:34:05.622Z",
                },
            ],
            "plan_items": [
                {
                    "id": "PLI-7893-0",
                    "plan_id": "PLAN-PROC-7893",
                    "product_snapshot_id": "SNP-CH3-MONITOR-01",
                    "title": 'ASUS TUF Gaming VG249Q1A 23.8" FHD 165Hz (144Hz+ Supported) IPS 1ms Gaming Monitor',
                    "unit_price": 129.99,
                    "quantity": 1,
                    "total_price": 129.99,
                    "currency": "USD",
                    "created_at": "2026-11-12T18:49:26.000Z",
                },
                {
                    "id": "PLI-001-1",
                    "plan_id": "PLAN-PROC-001",
                    "product_snapshot_id": "SNP-CH3-MON-4K",
                    "title": 'Dell UltraSharp U2723QE 27" 4K UHD IPS Black USB-C Hub Monitor & Thunderbolt Bundle',
                    "unit_price": 899.79,
                    "quantity": 1,
                    "total_price": 899.79,
                    "currency": "USD",
                    "created_at": "2026-11-11T15:34:05.623Z",
                },
            ],
            "approvals": [
                {
                    "id": "APPR-PROC-9735",
                    "plan_id": "PLAN-PROC-7893",
                    "plan_version": 1,
                    "approver_name": "Marcus Vance",
                    "approver_role": "VP of Finance",
                    "status": "APPROVED",
                    "approved_amount": 129.99,
                    "currency": "USD",
                    "comments": "Approved for live PayPal Sandbox execution ($129.99 USD).",
                    "decided_at": "2026-11-12T18:49:30.000Z",
                    "created_at": "2026-11-12T18:49:28.000Z",
                },
                {
                    "id": "APPR-PROC-001",
                    "plan_id": "PLAN-PROC-001",
                    "plan_version": 1,
                    "approver_name": "Marcus Vance",
                    "approver_role": "VP of Finance",
                    "status": "APPROVED",
                    "approved_amount": 899.79,
                    "currency": "USD",
                    "comments": "Approved for enterprise workstation deployment.",
                    "decided_at": "2026-11-11T16:00:00.000Z",
                    "created_at": "2026-11-11T15:40:00.000Z",
                },
                {
                    "id": "APPR-PROC-002",
                    "plan_id": "PLAN-PROC-002",
                    "plan_version": 1,
                    "approver_name": "Marcus Vance",
                    "approver_role": "VP of Finance",
                    "status": "APPROVED",
                    "approved_amount": 79.99,
                    "currency": "USD",
                    "comments": "Approved peripheral plan.",
                    "decided_at": "2026-11-12T15:00:00.000Z",
                    "created_at": "2026-11-12T14:40:00.000Z",
                },
            ],
            "payment_orders": [
                {
                    "id": "REDACTED_TEST_REFERENCE",
                    "plan_id": "PLAN-PROC-7893",
                    "approval_id": "APPR-PROC-9735",
                    "paypal_order_id": "REDACTED_TEST_REFERENCE",
                    "capture_id": "REDACTED_TEST_REFERENCE",
                    "amount": 129.99,
                    "currency": "USD",
                    "environment": "sandbox",
                    "status": "COMPLETED",
                    "checkout_url": "https://www.sandbox.paypal.com/checkoutnow?token=REDACTED_TEST_REFERENCE",
                    "payment_metadata": {
                        "order_status": "payment_completed",
                        "payment_stage": "PAYMENT COMPLETED",
                        "ultron_order_ref": "ORD-ULTRON-2026-2961",
                        "gateway": "PayPal REST v2 API (Live Sandbox)",
                        "intent": "CAPTURE",
                        "created_by": "ULTRON Financial Agent",
                        "checkout_url": "https://www.sandbox.paypal.com/checkoutnow?token=REDACTED_TEST_REFERENCE",
                        "paypal_order_id": "REDACTED_TEST_REFERENCE",
                        "paypal_remote_status": "COMPLETED",
                        "merchant_account": ULTRON_MERCHANT,
                        "merchant_email": ULTRON_MERCHANT["merchant_email"],
                        "buyer_email": "demo@example.invalid",
                        "payer_id": "UE7RD3EAWAEUJ",
                        "buyer_status": "VERIFIED_VIA_PAYPAL_API",
                        "buyer_approved_at": "2026-11-12T19:19:27.057Z",
                        "merchant_receiving_account": ULTRON_MERCHANT["merchant_email"],
                        "capture_time": "2026-11-12T19:19:28Z",
                        "verified_capture": True,
                        "capture_status": "COMPLETED",
                        "capture_channel": "PayPal Sandbox REST v2 API (Verified Live Capture)",
                    },
                    "created_at": "2026-11-12T18:49:32.000Z",
                    "updated_at": "2026-11-12T19:19:29.184Z",
                    "merchant_account": ULTRON_MERCHANT,
                },
                {
                    "id": PROTECTED_PAYMENT_ID,
                    "plan_id": "PLAN-PROC-001",
                    "approval_id": "APPR-PROC-001",
                    "paypal_order_id": PROTECTED_PAYPAL_ORDER_ID,
                    "capture_id": PROTECTED_CAPTURE_ID,
                    "amount": 899.79,
                    "currency": "USD",
                    "environment": "sandbox",
                    "status": "COMPLETED",
                    "checkout_url": None,
                    "payment_metadata": {
                        "payer_email": "demo@example.invalid",
                        "payer_name": "Demo Administrator",
                        "merchant_id": "ULTRON-ENT-SANDBOX-01",
                        "merchant_name": "ULTRON Autonomous Procurement Corp.",
                        "merchant_email": ULTRON_MERCHANT["merchant_email"],
                        "gateway": "PayPal REST v2 API",
                        "verified_capture": True,
                        "payment_stage": "PAYMENT COMPLETED",
                        "protection_note": "PERMANENT HISTORICAL RECORD: Read-only completed 899.79 USD Sandbox transaction. Must not be modified or re-captured.",
                        "merchant_account": ULTRON_MERCHANT,
                    },
                    "created_at": "2026-11-11T15:34:05.623Z",
                    "updated_at": "2026-11-12T14:34:05.623Z",
                    "merchant_account": ULTRON_MERCHANT,
                },
                {
                    "id": UNVERIFIED_PAYMENT_REF,
                    "plan_id": "PLAN-PROC-002",
                    "approval_id": "APPR-PROC-002",
                    "paypal_order_id": "UNVERIFIED",
                    "capture_id": None,
                    "amount": 79.99,
                    "currency": "USD",
                    "environment": "sandbox",
                    "status": "UNVERIFIED",
                    "checkout_url": None,
                    "payment_metadata": {
                        "order_status": "unverified",
                        "verification_status": "UNVERIFIED",
                        "ultron_order_ref": "ORD-ULTRON-2026-6727",
                        "protection_note": "UNVERIFIED TRANSACTION: Amount $79.99 USD with reference REDACTED_TEST_REFERENCE. Must remain UNVERIFIED unless its actual PayPal order and capture are confirmed directly through the PayPal Sandbox API.",
                        "merchant_account": ULTRON_MERCHANT,
                    },
                    "created_at": "2026-11-11T16:00:00.000Z",
                    "updated_at": "2026-11-11T16:00:00.000Z",
                    "merchant_account": ULTRON_MERCHANT,
                },
            ],
            "ai_runs": [
                {
                    "id": "AIR-9901",
                    "objective_id": "OBJ-46733",
                    "mission_id": "MSN-46733",
                    "provider": "OpenRouter / Deterministic",
                    "model": settings.OPENROUTER_MODEL,
                    "agent_role": "Procurement Planner & Spec Evaluator",
                    "prompt_summary": "Parse objective: Purchase a monitor with a minimum 144Hz refresh rate.",
                    "response_summary": "Selected ASUS TUF Gaming VG249Q1A 165Hz IPS Monitor ($129.99 USD) and prepared Plan PLAN-PROC-7893.",
                    "tokens_used": 384,
                    "latency_ms": 215,
                    "status": "SUCCESS",
                    "created_at": now,
                }
            ],
            "objective_events": [
                {
                    "id": "EVT-1001",
                    "objective_id": "OBJ-46733",
                    "event_type": "PAYMENT_CAPTURED",
                    "actor": "PayPal Sandbox REST v2",
                    "message": "PayPal Sandbox Order REDACTED_TEST_REFERENCE verified and captured (Capture ID: REDACTED_TEST_REFERENCE, Amount: $129.99 USD).",
                    "metadata_json": {
                        "paypal_order_id": "REDACTED_TEST_REFERENCE",
                        "capture_id": "REDACTED_TEST_REFERENCE",
                    },
                    "created_at": "2026-11-12T19:19:28.000Z",
                },
                {
                    "id": "EVT-1002",
                    "objective_id": "OBJ-1001",
                    "event_type": "PAYMENT_SETTLED",
                    "actor": "PayPal Sandbox REST v2",
                    "message": "Historical verified PayPal Sandbox settlement ($899.79 USD, Order: REDACTED_TEST_REFERENCE, Capture: REDACTED_TEST_REFERENCE).",
                    "metadata_json": {
                        "paypal_order_id": PROTECTED_PAYPAL_ORDER_ID,
                        "capture_id": PROTECTED_CAPTURE_ID,
                    },
                    "created_at": "2026-11-11T15:34:05.623Z",
                },
            ],
            "cart": [],
        }

    def _default_product_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "SNP-CH3-LAPTOP-01",
                "external_id": "ABC12345",
                "source": "Channel3",
                "title": 'Lenovo ThinkPad T480 Renewed Enterprise Laptop (14" FHD, Intel Core i5, 16GB RAM, 512GB NVMe SSD)',
                "description": "Commercial-grade enterprise laptop with 16GB DDR4 RAM, 512GB PCIe NVMe SSD, Thunderbolt 3, and 1-year vendor warranty.",
                "price": 189.99,
                "currency": "USD",
                "vendor": "Lenovo Authorized Refurbisher (Channel3)",
                "category": "laptop",
                "image_url": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://channel3.io/products/ABC12345",
                "rating": 4.7,
                "in_stock": True,
                "specs_json": {
                    "sku": "ABC12345",
                    "ram": "16GB DDR4",
                    "storage": "512GB NVMe SSD",
                    "cpu": "Intel Core i5-8350U",
                    "display": '14" 1080p IPS',
                    "warranty": "1-Year Commercial",
                },
                "created_at": "2026-11-11T15:00:00.000Z",
            },
            {
                "id": "SNP-CH3-LAPTOP-02",
                "external_id": "CH3-DELL-7490",
                "source": "Channel3",
                "title": 'Dell Latitude 7490 Business Ultrabook (14" FHD, Intel Core i7, 16GB RAM, 256GB SSD)',
                "description": "Lightweight enterprise ultrabook featuring 16GB RAM, 256GB M.2 SSD, Gigabit Ethernet, and Windows 11 Pro.",
                "price": 194.50,
                "currency": "USD",
                "vendor": "Dell Outlet Commercial Partner",
                "category": "laptop",
                "image_url": "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://channel3.io/products/CH3-DELL-7490",
                "rating": 4.6,
                "in_stock": True,
                "specs_json": {
                    "sku": "DELL-LAT-7490",
                    "ram": "16GB DDR4",
                    "storage": "256GB SSD",
                    "cpu": "Intel Core i7-8650U",
                    "display": '14" FHD Anti-Glare',
                    "warranty": "1-Year ProSupport",
                },
                "created_at": "2026-11-11T15:00:00.000Z",
            },
            {
                "id": "SNP-CH3-LAPTOP-03",
                "external_id": "CH3-ASUS-EXPERT",
                "source": "Channel3",
                "title": 'ASUS ExpertBook B1 Enterprise Laptop (15.6" FHD, Intel Core i7, 16GB RAM, 1TB NVMe SSD)',
                "description": "High-capacity developer workstation laptop with 16GB RAM, 1TB PCIe NVMe SSD, MIL-STD-810H durability.",
                "price": 689.00,
                "currency": "USD",
                "vendor": "ASUS Enterprise Channel3",
                "category": "laptop",
                "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://channel3.io/products/CH3-ASUS-EXPERT",
                "rating": 4.8,
                "in_stock": True,
                "specs_json": {
                    "sku": "ASUS-EXP-1TB",
                    "ram": "16GB DDR4",
                    "storage": "1TB NVMe SSD",
                    "cpu": "Intel Core i7-1255U",
                    "display": '15.6" FHD',
                    "warranty": "3-Year Enterprise",
                },
                "created_at": "2026-11-11T15:00:00.000Z",
            },
            {
                "id": "SNP-CH3-MONITOR-01",
                "external_id": "CH3-ASUS-VG249Q1A",
                "source": "Channel3",
                "title": 'ASUS TUF Gaming VG249Q1A 23.8" FHD 165Hz (144Hz+ Supported) IPS 1ms Gaming Monitor',
                "description": "165Hz (exceeds 144Hz minimum requirement) IPS display with 1ms MPRT response time, FreeSync Premium, DisplayPort & HDMI.",
                "price": 129.99,
                "currency": "USD",
                "vendor": "ASUS Official Store (Channel3 Partner)",
                "category": "monitor",
                "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://channel3.io/products/CH3-ASUS-VG249Q1A",
                "rating": 4.8,
                "in_stock": True,
                "specs_json": {
                    "sku": "VG249Q1A-165HZ",
                    "refresh_rate": "165Hz (144Hz+ Native)",
                    "panel": "IPS",
                    "resolution": "1920x1080 FHD",
                    "response_time": "1ms",
                },
                "created_at": "2026-11-11T15:00:00.000Z",
            },
            {
                "id": "SNP-CH3-GPU-01",
                "external_id": "RTX4090-24GB",
                "source": "Channel3",
                "title": "NVIDIA GeForce RTX 4090 24GB GDDR6X Enterprise Compute & AI Accelerator",
                "description": "Flagship 24GB GDDR6X GPU with 16,384 CUDA cores for local LLM inference, deep learning, and 3D rendering.",
                "price": 1799.00,
                "currency": "USD",
                "vendor": "NVIDIA Authorized Tier-1 Distributor",
                "category": "gpu",
                "image_url": "https://images.unsplash.com/photo-1591488320449-011701bb6704?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://channel3.io/products/RTX4090-24GB",
                "rating": 4.9,
                "in_stock": True,
                "specs_json": {
                    "sku": "RTX4090-24GB",
                    "vram": "24GB GDDR6X",
                    "cuda_cores": "16384",
                    "interface": "PCIe 4.0 x16",
                    "warranty": "3-Year Manufacturer",
                },
                "created_at": "2026-11-11T15:00:00.000Z",
            },
            {
                "id": "SNP-CH3-GPU-02",
                "external_id": "RX7900XTX-24GB",
                "source": "Channel3",
                "title": "AMD Radeon RX 7900 XTX 24GB GDDR6 Workstation Graphics Card",
                "description": "High-bandwidth 24GB GDDR6 GPU accelerator with DisplayPort 2.1 and ROCm compute support.",
                "price": 949.99,
                "currency": "USD",
                "vendor": "Sapphire Commercial Channel3",
                "category": "gpu",
                "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://channel3.io/products/RX7900XTX-24GB",
                "rating": 4.7,
                "in_stock": True,
                "specs_json": {
                    "sku": "RX7900XTX-24GB",
                    "vram": "24GB GDDR6",
                    "interface": "PCIe 4.0 x16",
                    "warranty": "3-Year Commercial",
                },
                "created_at": "2026-11-11T15:00:00.000Z",
            },
            {
                "id": "SNP-CH3-CHAIR-01",
                "external_id": "CH3-ERGO-CHAIR-89",
                "source": "Channel3",
                "title": "ULTRON ErgoMesh Pro Executive Office Chair with Lumbar Support & Breathable Mesh",
                "description": "Commercial BIFMA-certified ergonomic office chair with adjustable lumbar support, armrests, and heavy-duty casters.",
                "price": 84.99,
                "currency": "USD",
                "vendor": "Workspace Furnishings Direct (Channel3)",
                "category": "chair",
                "image_url": "https://images.unsplash.com/photo-1505843490538-5133c6c7d0e1?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://channel3.io/products/CH3-ERGO-CHAIR-89",
                "rating": 4.6,
                "in_stock": True,
                "specs_json": {
                    "sku": "ERGO-CHAIR-89",
                    "certification": "BIFMA X5.1",
                    "weight_capacity": "300 lbs",
                    "warranty": "5-Year Frame",
                },
                "created_at": "2026-11-11T15:00:00.000Z",
            },
            {
                "id": "SNP-CH3-PHONE-01",
                "external_id": "CH3-PIXEL-256",
                "source": "Channel3",
                "title": "Samsung Galaxy A54 5G Unlocked Enterprise Smartphone (256GB Storage, 50MP OIS Camera)",
                "description": "Enterprise-ready unlocked 5G smartphone featuring 256GB storage, 8GB RAM, 50MP Optical Image Stabilization camera, and 120Hz AMOLED display.",
                "price": 349.99,
                "currency": "USD",
                "vendor": "Samsung Business Direct (Channel3)",
                "category": "smartphone",
                "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://channel3.io/products/CH3-PIXEL-256",
                "rating": 4.7,
                "in_stock": True,
                "specs_json": {
                    "sku": "GALAXY-A54-256GB",
                    "storage": "256GB",
                    "ram": "8GB",
                    "camera": "50MP OIS Triple Camera",
                    "display": '6.4" 120Hz Super AMOLED',
                },
                "created_at": "2026-11-11T15:00:00.000Z",
            },
        ]

    def _load_state(self) -> Dict[str, Any]:
        default_state = self._default_seed_state()
        if DB_JSON_FILE.exists():
            try:
                raw = json.loads(DB_JSON_FILE.read_text(encoding="utf-8"))
                for key, val in default_state.items():
                    if key not in raw or not isinstance(raw[key], list):
                        raw[key] = val
                self.save_state(raw)
                return raw
            except Exception:
                pass
        self.save_state(default_state)
        return default_state

    def save_state(self, state: Optional[Dict[str, Any]] = None) -> None:
        target = state if state is not None else self.state
        DB_JSON_FILE.write_text(json.dumps(target, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # Dashboard & Audit Queries
    # -------------------------------------------------------------------------
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        objectives = self.state.get("objectives", [])
        missions = self.state.get("missions", [])
        approvals = self.state.get("approvals", [])
        plans = self.state.get("plans", [])
        payments = self.state.get("payment_orders", [])
        ai_runs = self.state.get("ai_runs", [])
        events = self.state.get("objective_events", [])

        completed_payments = [p for p in payments if p.get("status") == "COMPLETED"]
        settled_val = sum(float(p.get("amount") or 0) for p in completed_payments)
        proposed_val = sum(
            float(pl.get("total_amount") or 0)
            for pl in plans
            if pl.get("status") in ("SUBMITTED", "APPROVED")
        )

        active_provider = (
            f"Groq ({settings.GROQ_MODEL})"
            if settings.is_groq_configured
            else f"OpenRouter ({settings.OPENROUTER_MODEL})"
            if settings.is_openrouter_configured
            else "Deterministic Python Engine (Configure OPENROUTER_API_KEY in .env for LLM)"
        )

        return {
            "total_objectives": len(objectives),
            "completed_objectives": sum(1 for o in objectives if o.get("status") == "COMPLETED"),
            "active_objectives": sum(1 for o in objectives if o.get("status") != "COMPLETED"),
            "running_missions": sum(
                1 for m in missions if m.get("status") in ("RUNNING", "REPLANNING")
            ),
            "pending_approvals": sum(1 for a in approvals if a.get("status") == "PENDING"),
            "proposed_purchase_value": round(proposed_val, 2),
            "completed_sandbox_payments_value": round(settled_val, 2),
            "completed_sandbox_payments_count": len(completed_payments),
            "total_ai_operations": len(ai_runs),
            "system_health": {
                "database": self.mysql_status_message,
                "ai_provider": active_provider,
                "paypal_sandbox": "PayPal Sandbox REST v2",
            },
            "recent_activity": sorted(
                events, key=lambda e: e.get("created_at", ""), reverse=True
            )[:12],
        }

    # -------------------------------------------------------------------------
    # Objectives, Missions, Plans, Approvals
    # -------------------------------------------------------------------------
    def get_objectives(self) -> List[Dict[str, Any]]:
        constraints = self.state.get("constraints", [])
        result = []
        for obj in self.state.get("objectives", []):
            item = dict(obj)
            item["constraints"] = [
                c for c in constraints if c.get("objective_id") == obj.get("id")
            ]
            result.append(item)
        return result

    def get_objective_by_id(self, obj_id: str) -> Optional[Dict[str, Any]]:
        for obj in self.get_objectives():
            if obj.get("id") == obj_id:
                obj["plans"] = [
                    p for p in self.get_plans() if p.get("objective_id") == obj_id
                ]
                obj["missions"] = [
                    m for m in self.state.get("missions", []) if m.get("objective_id") == obj_id
                ]
                obj["events"] = [
                    e
                    for e in self.state.get("objective_events", [])
                    if e.get("objective_id") == obj_id
                ]
                return obj
        return None

    def create_objective(
        self,
        title: str,
        description: str,
        budget_limit: Optional[float] = None,
        currency: str = "USD",
        constraints: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        now = _utc_now_iso()
        suffix = str(int(time.time() * 1000))[-5:]
        obj_id = f"OBJ-{suffix}"
        new_obj = {
            "id": obj_id,
            "user_id": "usr-admin-01",
            "title": title,
            "description": description,
            "status": "PLANNING",
            "budget_limit": budget_limit,
            "currency": currency or "USD",
            "created_at": now,
            "updated_at": now,
        }
        self.state["objectives"].insert(0, new_obj)

        created_constraints = []
        for idx, c in enumerate(constraints or []):
            c_obj = {
                "id": f"CST-{suffix}-{idx}",
                "objective_id": obj_id,
                "constraint_type": c.get("constraint_type", "quality_tier"),
                "constraint_value": c.get("constraint_value", ""),
                "is_hard_constraint": bool(c.get("is_hard_constraint", True)),
                "created_at": now,
            }
            self.state["constraints"].append(c_obj)
            created_constraints.append(c_obj)

        self.log_event(
            obj_id,
            "OBJECTIVE_CREATED",
            "ULTRON Planner Agent",
            f"Objective '{title}' registered with budget {budget_limit if budget_limit is not None else 'Open'} {currency}.",
            {"budget_limit": budget_limit, "currency": currency},
        )
        self.save_state()
        out = dict(new_obj)
        out["constraints"] = created_constraints
        return out

    def log_event(
        self,
        objective_id: str,
        event_type: str,
        actor: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ev = {
            "id": f"EVT-{str(int(time.time() * 1000))[-6:]}",
            "objective_id": objective_id,
            "event_type": event_type,
            "actor": actor,
            "message": message,
            "metadata_json": metadata or {},
            "created_at": _utc_now_iso(),
        }
        self.state.setdefault("objective_events", []).insert(0, ev)
        self.save_state()
        return ev

    def log_ai_run(
        self,
        provider: str,
        model: str,
        agent_role: str,
        prompt_summary: str,
        response_summary: str,
        tokens_used: int = 0,
        latency_ms: int = 0,
        status: str = "SUCCESS",
        objective_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        run = {
            "id": f"AIR-{str(int(time.time() * 1000))[-6:]}",
            "objective_id": objective_id,
            "mission_id": mission_id,
            "provider": provider,
            "model": model,
            "agent_role": agent_role,
            "prompt_summary": prompt_summary,
            "response_summary": response_summary,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "status": status,
            "created_at": _utc_now_iso(),
        }
        self.state.setdefault("ai_runs", []).insert(0, run)
        self.save_state()
        return run

    def get_plans(self) -> List[Dict[str, Any]]:
        items = self.state.get("plan_items", [])
        approvals = self.state.get("approvals", [])
        result = []
        for pl in self.state.get("plans", []):
            item = dict(pl)
            item["items"] = [i for i in items if i.get("plan_id") == pl.get("id")]
            item["approvals"] = [a for a in approvals if a.get("plan_id") == pl.get("id")]
            result.append(item)
        return result

    def get_plan_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        for pl in self.get_plans():
            if pl.get("id") == plan_id:
                return pl
        return None

    def create_plan(
        self,
        objective_id: str,
        notes: str,
        items_input: List[Dict[str, Any]],
        currency: str = "USD",
    ) -> Dict[str, Any]:
        now = _utc_now_iso()
        suffix = str(int(time.time() * 1000))[-4:]
        plan_id = f"PLAN-PROC-{suffix}"

        existing_versions = [
            int(p.get("version", 1))
            for p in self.state.get("plans", [])
            if p.get("objective_id") == objective_id
        ]
        version = max(existing_versions, default=0) + 1

        plan_items = []
        total_amount = 0.0
        for idx, raw_it in enumerate(items_input):
            snap_id = raw_it.get("product_snapshot_id", "")
            snap = next(
                (
                    s
                    for s in self.state.get("product_snapshots", [])
                    if s.get("id") == snap_id or s.get("external_id") == snap_id
                ),
                None,
            )
            unit_price = float(
                raw_it.get("unit_price")
                if raw_it.get("unit_price") is not None
                else (snap.get("price", 99.99) if snap else 99.99)
            )
            qty = max(1, int(raw_it.get("quantity", 1)))
            line_total = round(unit_price * qty, 2)
            total_amount = round(total_amount + line_total, 2)
            title = raw_it.get("title") or (snap.get("title") if snap else "Procurement Item")
            pi = {
                "id": f"PLI-{suffix}-{idx}",
                "plan_id": plan_id,
                "product_snapshot_id": snap.get("id") if snap else snap_id,
                "title": title,
                "unit_price": unit_price,
                "quantity": qty,
                "total_price": line_total,
                "currency": currency,
                "created_at": now,
            }
            self.state.setdefault("plan_items", []).append(pi)
            plan_items.append(pi)

        new_plan = {
            "id": plan_id,
            "objective_id": objective_id,
            "version": version,
            "status": "SUBMITTED",
            "total_amount": total_amount,
            "currency": currency,
            "notes": notes or f"Autonomous Purchase Plan ({len(plan_items)} line items).",
            "created_at": now,
            "updated_at": now,
        }
        self.state.setdefault("plans", []).insert(0, new_plan)

        # Create Pending Approval Checkpoint automatically
        appr = {
            "id": f"APPR-PROC-{str(int(time.time() * 1000))[-4:]}",
            "plan_id": plan_id,
            "plan_version": version,
            "approver_name": "Marcus Vance",
            "approver_role": "VP of Finance",
            "status": "PENDING",
            "approved_amount": total_amount,
            "currency": currency,
            "comments": "Awaiting executive sign-off before PayPal Sandbox order creation.",
            "decided_at": None,
            "created_at": now,
        }
        self.state.setdefault("approvals", []).insert(0, appr)

        for obj in self.state.get("objectives", []):
            if obj.get("id") == objective_id:
                obj["status"] = "AWAITING_APPROVAL"
                obj["updated_at"] = now

        self.log_event(
            objective_id,
            "PLAN_SUBMITTED",
            "ULTRON Procurement Agent",
            f"Purchase Plan {plan_id} (v{version}) created for ${total_amount:.2f} {currency}. Routed to {appr['id']} for human approval.",
            {"plan_id": plan_id, "approval_id": appr["id"], "total_amount": total_amount},
        )
        self.save_state()
        return self.get_plan_by_id(plan_id) or new_plan

    def get_approvals(self) -> List[Dict[str, Any]]:
        return self.state.get("approvals", [])

    def decide_approval(
        self, approval_id: str, decision: str, comments: Optional[str] = None
    ) -> Dict[str, Any]:
        now = _utc_now_iso()
        target = None
        for a in self.state.get("approvals", []):
            if a.get("id") == approval_id:
                target = a
                break
        if not target:
            raise ValueError(f"Approval record {approval_id} not found.")

        target["status"] = decision
        target["decided_at"] = now
        if comments:
            target["comments"] = comments

        plan_id = target.get("plan_id")
        objective_id = None
        for pl in self.state.get("plans", []):
            if pl.get("id") == plan_id:
                pl["status"] = "APPROVED" if decision == "APPROVED" else "REJECTED"
                pl["updated_at"] = now
                objective_id = pl.get("objective_id")

        if objective_id:
            for obj in self.state.get("objectives", []):
                if obj.get("id") == objective_id:
                    obj["status"] = "APPROVED" if decision == "APPROVED" else "PLANNING"
                    obj["updated_at"] = now
            self.log_event(
                objective_id,
                f"APPROVAL_{decision}",
                target.get("approver_name", "VP of Finance"),
                f"Governance checkpoint {approval_id} for Plan {plan_id} marked {decision}.",
                {"approval_id": approval_id, "plan_id": plan_id, "decision": decision},
            )

        self.save_state()
        return target

    # -------------------------------------------------------------------------
    # Payment Orders & Buyer Config
    # -------------------------------------------------------------------------
    def get_payment_orders(self) -> List[Dict[str, Any]]:
        return self.state.get("payment_orders", [])

    def get_payment_order_by_id(self, order_id_or_token: str) -> Optional[Dict[str, Any]]:
        for p in self.state.get("payment_orders", []):
            if (
                p.get("id") == order_id_or_token
                or p.get("paypal_order_id") == order_id_or_token
            ):
                return p
        return None

    def get_buyer_config(self) -> Dict[str, Any]:
        default_cfg = {
            "buyer_email": settings.PAYPAL_BUYER_EMAIL or "demo@example.invalid",
            "account_type": "Personal (Buyer)",
            "environment": "SANDBOX",
            "checkout_url": "https://sandbox.paypal.com",
            "api_url": settings.PAYPAL_BASE_URL or "https://api-m.sandbox.paypal.com",
            "merchant_email": ULTRON_MERCHANT["merchant_email"],
            "connection_status": "Configured",
            "last_tested_at": None,
            "last_test_details": None,
        }
        if BUYER_CONFIG_FILE.exists():
            try:
                saved = json.loads(BUYER_CONFIG_FILE.read_text(encoding="utf-8"))
                default_cfg.update(saved)
            except Exception:
                pass
        return default_cfg

    def update_buyer_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_buyer_config()
        buyer_email = (updates.get("buyer_email") or current["buyer_email"]).strip()
        if not buyer_email or "@" not in buyer_email:
            raise ValueError("Valid Sandbox Personal buyer email is required.")
        if buyer_email.lower() == ULTRON_MERCHANT["merchant_email"].lower():
            raise ValueError(
                "Buyer Personal account email must be separate from the Merchant Business account."
            )
        current["buyer_email"] = buyer_email
        if "connection_status" in updates:
            current["connection_status"] = updates["connection_status"]
        if "last_tested_at" in updates:
            current["last_tested_at"] = updates["last_tested_at"]
        if "last_test_details" in updates:
            current["last_test_details"] = updates["last_test_details"]
        BUYER_CONFIG_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return current

    # -------------------------------------------------------------------------
    # Disposable Test Records Cleanup (Preserves Genuine PayPal Transactions)
    # -------------------------------------------------------------------------
    def _is_protected_payment(self, p: Dict[str, Any]) -> bool:
        pid = p.get("id", "")
        pp_ord = p.get("paypal_order_id", "")
        cap_id = p.get("capture_id") or ""
        if pid in (PROTECTED_PAYMENT_ID, UNVERIFIED_PAYMENT_REF, "REDACTED_TEST_REFERENCE", "REDACTED_TEST_REFERENCE"):
            return True
        if pp_ord in (PROTECTED_PAYPAL_ORDER_ID, "REDACTED_TEST_REFERENCE", "REDACTED_TEST_REFERENCE"):
            return True
        # Any genuine external PayPal order ID (not starting with SANDBOX-ORD- or EC-SBOX-)
        if (
            pp_ord
            and pp_ord != "UNVERIFIED"
            and not pp_ord.startswith("SANDBOX-ORD-")
            and not pp_ord.startswith("EC-SBOX-")
        ):
            return True
        if cap_id and not cap_id.startswith("CAPTURE-SANDBOX-"):
            return True
        return False

    def preview_test_records_cleanup(self) -> Dict[str, Any]:
        payments = self.state.get("payment_orders", [])
        disposable = [p for p in payments if not self._is_protected_payment(p)]
        preserved = [p for p in payments if self._is_protected_payment(p)]
        return {
            "disposable_count": len(disposable),
            "disposable_payments": disposable,
            "preserved_count": len(preserved),
            "preserved_records": preserved,
            "required_confirmation_phrase": "CLEAR TEST DATA",
        }

    def execute_test_records_cleanup(
        self, admin_email: str, confirmation_phrase: str, final_confirmed: bool
    ) -> Dict[str, Any]:
        if confirmation_phrase != "CLEAR TEST DATA" or not final_confirmed:
            raise ValueError("Confirmation phrase 'CLEAR TEST DATA' and final confirmation are required.")
        preview = self.preview_test_records_cleanup()
        preserved_ids = {p["id"] for p in preview["preserved_records"]}
        removed_payments = [
            p for p in self.state.get("payment_orders", []) if p.get("id") not in preserved_ids
        ]
        self.state["payment_orders"] = [
            p for p in self.state.get("payment_orders", []) if p.get("id") in preserved_ids
        ]
        self.save_state()
        return {
            "status": "SUCCESS",
            "admin_email": admin_email,
            "removed_payments_count": len(removed_payments),
            "preserved_records_count": len(preview["preserved_records"]),
            "cleaned_at": _utc_now_iso(),
        }


db_manager = DatabaseManager()
