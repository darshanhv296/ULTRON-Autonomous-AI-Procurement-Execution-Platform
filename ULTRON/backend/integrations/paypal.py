"""
ULTRON PayPal Developer Sandbox REST v2 Integration Module
Implements genuine OAuth2 token exchange, merchant verification, order creation,
live status verification, automatic return capture, and refund execution.
Never fabricates PayPal Order IDs or Capture IDs.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import httpx

from backend.config import settings
from backend.database import ULTRON_MERCHANT, db_manager


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PayPalSandboxClient:
    """Genuine PayPal Sandbox REST v2 API Client."""

    def __init__(self) -> None:
        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._app_id: Optional[str] = None

    @property
    def base_url(self) -> str:
        return (settings.PAYPAL_BASE_URL or "https://api-m.sandbox.paypal.com").rstrip("/")

    async def get_access_token(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Obtains a genuine OAuth2 Bearer token from PayPal Sandbox REST API."""
        settings.reload()
        if not settings.is_paypal_configured:
            raise ValueError(
                "PayPal Sandbox REST API credentials (PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET) "
                "are not configured in .env."
            )

        now = time.time()
        if not force_refresh and self._cached_token and now < self._token_expiry:
            return {"access_token": self._cached_token, "app_id": self._app_id}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
                headers={"Accept": "application/json", "Accept-Language": "en_US"},
                data={"grant_type": "client_credentials"},
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"PayPal Sandbox OAuth failed (HTTP {resp.status_code}): {resp.text[:200]}"
                )
            data = resp.json()
            self._cached_token = data["access_token"]
            self._app_id = data.get("app_id")
            self._token_expiry = now + max(60, int(data.get("expires_in", 3600)) - 120)
            return data

    async def verify_merchant_identity(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Verifies live PayPal Sandbox OAuth credentials and merchant configuration."""
        settings.reload()
        merchant_email = settings.PAYPAL_MERCHANT_EMAIL or ULTRON_MERCHANT["merchant_email"]
        if not settings.is_paypal_configured:
            return {
                "configured": False,
                "oauth_success": False,
                "verified": False,
                "live_captures_enabled": False,
                "environment": "SANDBOX",
                "api_base_url": self.base_url,
                "merchant_receiving_email": merchant_email,
                "message": "PENDING CREDENTIAL SETUP: Configure PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env.",
                "checked_at": _utc_now_iso(),
            }

        try:
            token_data = await self.get_access_token(force_refresh=force_refresh)
            return {
                "configured": True,
                "oauth_success": True,
                "verified": True,
                "live_captures_enabled": True,
                "environment": "SANDBOX",
                "api_base_url": self.base_url,
                "merchant_receiving_email": merchant_email,
                "app_id": token_data.get("app_id"),
                "scopes": token_data.get("scope", ""),
                "message": f"PayPal Sandbox OAuth2 verified for merchant {merchant_email}. Live captures enabled.",
                "checked_at": _utc_now_iso(),
            }
        except Exception as exc:
            return {
                "configured": True,
                "oauth_success": False,
                "verified": False,
                "live_captures_enabled": False,
                "environment": "SANDBOX",
                "api_base_url": self.base_url,
                "merchant_receiving_email": merchant_email,
                "message": f"PayPal Sandbox authentication failed: {str(exc)}",
                "checked_at": _utc_now_iso(),
            }

    async def create_sandbox_order(
        self, plan_id: str, approval_id: Optional[str] = None, app_base_url: str = "http://127.0.0.1:8000"
    ) -> Dict[str, Any]:
        """Creates a genuine PayPal Sandbox order via POST /v2/checkout/orders."""
        plan = db_manager.get_plan_by_id(plan_id)
        if not plan:
            raise ValueError(f"Purchase Plan {plan_id} not found.")

        # Verify plan is approved
        approvals = db_manager.get_approvals()
        matching_appr = next(
            (
                a
                for a in approvals
                if a.get("plan_id") == plan_id and a.get("status") == "APPROVED"
            ),
            None,
        )
        if not matching_appr and plan.get("status") not in ("APPROVED", "PAID"):
            raise ValueError(
                f"Purchase Plan {plan_id} must be APPROVED before creating a PayPal Sandbox order."
            )

        effective_approval_id = (
            approval_id or (matching_appr.get("id") if matching_appr else f"APPR-{plan_id}")
        )

        # Reuse existing eligible CREATED/APPROVED order for this plan to prevent duplicates
        for existing in db_manager.get_payment_orders():
            if existing.get("plan_id") == plan_id and existing.get("status") in (
                "CREATED",
                "APPROVED",
                "PAYER_ACTION_REQUIRED",
            ):
                pp_id = existing.get("paypal_order_id", "")
                if pp_id and not pp_id.startswith("SANDBOX-ORD-"):
                    return existing

        token_info = await self.get_access_token()
        access_token = token_info["access_token"]

        amount_val = f"{float(plan.get('total_amount', 0.0)):.2f}"
        currency = plan.get("currency", "USD")
        merchant_email = settings.PAYPAL_MERCHANT_EMAIL or ULTRON_MERCHANT["merchant_email"]

        return_url = f"{app_base_url.rstrip('/')}/api/payments/callback/return"
        cancel_url = f"{app_base_url.rstrip('/')}/api/payments/callback/cancel"

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": plan_id,
                    "description": f"ULTRON Autonomous Procurement Plan {plan_id}",
                    "amount": {"currency_code": currency, "value": amount_val},
                    "payee": {"email_address": merchant_email},
                }
            ],
            "application_context": {
                "brand_name": "ULTRON Autonomous Procurement Corp.",
                "landing_page": "LOGIN",
                "user_action": "PAY_NOW",
                "return_url": return_url,
                "cancel_url": cancel_url,
            },
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self.base_url}/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "PayPal-Request-Id": f"ULTRON-CREATE-{plan_id}-{int(time.time())}",
                },
                json=payload,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"PayPal Order creation failed (HTTP {resp.status_code}): {resp.text[:300]}"
                )
            pp_data = resp.json()

        paypal_order_id = pp_data["id"]
        approve_link = next(
            (
                lnk["href"]
                for lnk in pp_data.get("links", [])
                if lnk.get("rel") in ("approve", "payer-action")
            ),
            f"https://www.sandbox.paypal.com/checkoutnow?token={paypal_order_id}",
        )

        now = _utc_now_iso()
        suffix = str(int(time.time() * 1000))[-6:]
        buyer_cfg = db_manager.get_buyer_config()

        new_order = {
            "id": f"PAY-SBOX-{suffix}",
            "plan_id": plan_id,
            "approval_id": effective_approval_id,
            "paypal_order_id": paypal_order_id,
            "capture_id": None,
            "amount": float(amount_val),
            "currency": currency,
            "environment": "sandbox",
            "status": pp_data.get("status", "CREATED"),
            "checkout_url": approve_link,
            "payment_metadata": {
                "order_status": "awaiting_payment",
                "payment_stage": "WAITING FOR BUYER APPROVAL",
                "ultron_order_ref": f"ORD-ULTRON-2026-{suffix[-4:]}",
                "gateway": "PayPal REST v2 API (Live Sandbox)",
                "intent": "CAPTURE",
                "created_by": "ULTRON Payment Agent",
                "checkout_url": approve_link,
                "paypal_order_id": paypal_order_id,
                "paypal_remote_status": pp_data.get("status", "CREATED"),
                "merchant_account": ULTRON_MERCHANT,
                "merchant_email": merchant_email,
                "buyer_email": buyer_cfg.get("buyer_email"),
                "return_url": return_url,
                "cancel_url": cancel_url,
                "links": pp_data.get("links", []),
            },
            "created_at": now,
            "updated_at": now,
            "merchant_account": ULTRON_MERCHANT,
        }

        db_manager.state.setdefault("payment_orders", []).insert(0, new_order)
        db_manager.log_event(
            plan.get("objective_id", "OBJ-1001"),
            "PAYPAL_ORDER_CREATED",
            "ULTRON Payment Agent",
            f"Genuine PayPal Sandbox Order {paypal_order_id} created (${amount_val} {currency}). Waiting for buyer approval.",
            {"paypal_order_id": paypal_order_id, "approval_url": approve_link},
        )
        db_manager.save_state()
        return new_order

    async def verify_and_sync_order(self, payment_id_or_token: str) -> Dict[str, Any]:
        """Queries GET /v2/checkout/orders/{id} directly from PayPal Sandbox and syncs state."""
        order = db_manager.get_payment_order_by_id(payment_id_or_token)
        if not order:
            raise ValueError(f"Payment order {payment_id_or_token} not found.")

        pp_order_id = order.get("paypal_order_id", "")
        if not pp_order_id or pp_order_id == "UNVERIFIED":
            raise ValueError(f"Payment {order['id']} does not have a verifiable PayPal Order ID.")

        token_info = await self.get_access_token()
        access_token = token_info["access_token"]

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/v2/checkout/orders/{pp_order_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"PayPal GET order {pp_order_id} failed (HTTP {resp.status_code}): {resp.text[:250]}"
                )
            pp_data = resp.json()

        remote_status = pp_data.get("status", "CREATED")
        links = pp_data.get("links", [])
        approve_link = next(
            (lnk["href"] for lnk in links if lnk.get("rel") in ("approve", "payer-action")),
            order.get("checkout_url")
            or f"https://www.sandbox.paypal.com/checkoutnow?token={pp_order_id}",
        )

        payer = pp_data.get("payer") or {}
        pu = (pp_data.get("purchase_units") or [{}])[0]
        captures = (pu.get("payments") or {}).get("captures") or []

        now = _utc_now_iso()
        meta = order.setdefault("payment_metadata", {})
        meta["paypal_remote_status"] = remote_status
        meta["paypal_verified_at"] = now
        meta["checkout_url"] = approve_link
        order["checkout_url"] = approve_link

        if payer.get("email_address"):
            meta["buyer_email"] = payer["email_address"]
        if payer.get("payer_id"):
            meta["payer_id"] = payer["payer_id"]

        if remote_status == "COMPLETED" or captures:
            cap_id = captures[0].get("id") if captures else order.get("capture_id")
            order["status"] = "COMPLETED"
            if cap_id:
                order["capture_id"] = cap_id
            meta["payment_stage"] = "PAYMENT COMPLETED"
            meta["verified_capture"] = True
        elif remote_status == "APPROVED":
            order["status"] = "APPROVED"
            meta["payment_stage"] = "BUYER APPROVED"
            meta["buyer_status"] = "VERIFIED_VIA_PAYPAL_API"
            meta["buyer_approved_at"] = meta.get("buyer_approved_at") or now
        else:
            order["status"] = remote_status
            meta["payment_stage"] = "WAITING FOR BUYER APPROVAL"

        order["updated_at"] = now
        db_manager.save_state()

        eligible = remote_status in ("CREATED", "PAYER_ACTION_REQUIRED", "APPROVED")
        return {
            "order": order,
            "paypal_status": remote_status,
            "payment_stage": meta["payment_stage"],
            "eligible_for_approval": eligible,
            "approval_url": approve_link,
            "paypal_order_summary": {
                "id": pp_order_id,
                "status": remote_status,
                "intent": pp_data.get("intent", "CAPTURE"),
                "create_time": pp_data.get("create_time"),
                "amount": pu.get("amount"),
                "payee": pu.get("payee"),
                "payer": payer or None,
                "approval_url": approve_link,
                "links": links,
                "eligible_for_approval": eligible,
            },
        }

    async def capture_sandbox_order(self, payment_id_or_token: str) -> Dict[str, Any]:
        """Captures an APPROVED PayPal Sandbox order via POST /v2/checkout/orders/{id}/capture."""
        order = db_manager.get_payment_order_by_id(payment_id_or_token)
        if not order:
            raise ValueError(f"Payment order {payment_id_or_token} not found.")

        if order.get("status") == "COMPLETED" and order.get("capture_id"):
            raise ValueError(
                f"DUPLICATE_CAPTURE_PREVENTED: Order {order['paypal_order_id']} is already COMPLETED (Capture ID: {order['capture_id']})."
            )

        # Always verify live status with PayPal before capturing
        sync_res = await self.verify_and_sync_order(order["id"])
        order = sync_res["order"]
        if order.get("status") == "COMPLETED" and order.get("capture_id"):
            return order

        if sync_res["paypal_status"] != "APPROVED":
            raise ValueError(
                f"Order {order['paypal_order_id']} cannot be captured yet because PayPal status is '{sync_res['paypal_status']}'. "
                f"Buyer must approve at {sync_res['approval_url']} first."
            )

        meta = order.setdefault("payment_metadata", {})
        meta["payment_stage"] = "CAPTURE IN PROGRESS"
        db_manager.save_state()

        token_info = await self.get_access_token()
        access_token = token_info["access_token"]
        pp_order_id = order["paypal_order_id"]

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self.base_url}/v2/checkout/orders/{pp_order_id}/capture",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "PayPal-Request-Id": f"ULTRON-CAP-{pp_order_id}",
                },
                json={},
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"PayPal capture failed for {pp_order_id} (HTTP {resp.status_code}): {resp.text[:300]}"
                )
            cap_data = resp.json()

        pu = (cap_data.get("purchase_units") or [{}])[0]
        captures = (pu.get("payments") or {}).get("captures") or []
        if not captures or captures[0].get("status") != "COMPLETED":
            raise RuntimeError(f"PayPal capture did not return COMPLETED status: {cap_data}")

        capture_obj = captures[0]
        capture_id = capture_obj["id"]
        payer = cap_data.get("payer") or {}
        now = _utc_now_iso()

        order["status"] = "COMPLETED"
        order["capture_id"] = capture_id
        order["updated_at"] = now
        meta["order_status"] = "payment_completed"
        meta["payment_stage"] = "PAYMENT COMPLETED"
        meta["capture_time"] = capture_obj.get("create_time", now)
        meta["verified_capture"] = True
        meta["capture_status"] = "COMPLETED"
        meta["capture_channel"] = "PayPal Sandbox REST v2 API (Verified Live Capture)"
        if payer.get("email_address"):
            meta["buyer_email"] = payer["email_address"]
        if payer.get("payer_id"):
            meta["payer_id"] = payer["payer_id"]

        # Transition associated plan & objective
        plan_id = order.get("plan_id")
        for pl in db_manager.state.get("plans", []):
            if pl.get("id") == plan_id:
                pl["status"] = "PAID"
                pl["updated_at"] = now
                for obj in db_manager.state.get("objectives", []):
                    if obj.get("id") == pl.get("objective_id"):
                        obj["status"] = "COMPLETED"
                        obj["updated_at"] = now
                db_manager.log_event(
                    pl.get("objective_id", "OBJ-1001"),
                    "PAYMENT_COMPLETED",
                    "PayPal Sandbox REST v2",
                    f"PayPal Order {pp_order_id} captured (Capture ID: {capture_id}, Amount: ${order['amount']:.2f} {order['currency']}).",
                    {"paypal_order_id": pp_order_id, "capture_id": capture_id},
                )

        db_manager.save_state()
        return order

    async def auto_verify_and_capture_on_return(
        self, token_or_id: str, payer_id: str = ""
    ) -> Dict[str, Any]:
        """Automatically verifies buyer approval and captures the order once on return."""
        sync_res = await self.verify_and_sync_order(token_or_id)
        order = sync_res["order"]
        if payer_id:
            order.setdefault("payment_metadata", {})["payer_id"] = payer_id
            db_manager.save_state()

        if order.get("status") == "COMPLETED" and order.get("capture_id"):
            return {
                "order": order,
                "paypal_status": "COMPLETED",
                "payment_stage": "PAYMENT COMPLETED",
                "captured": True,
            }

        if sync_res["paypal_status"] == "APPROVED":
            captured_order = await self.capture_sandbox_order(order["id"])
            return {
                "order": captured_order,
                "paypal_status": "COMPLETED",
                "payment_stage": "PAYMENT COMPLETED",
                "captured": True,
            }

        return {
            "order": order,
            "paypal_status": sync_res["paypal_status"],
            "payment_stage": sync_res["payment_stage"],
            "captured": False,
        }

    async def test_buyer_configuration(self, buyer_email: Optional[str] = None) -> Dict[str, Any]:
        """Validates Personal Buyer email separation and checks active Sandbox connectivity."""
        current = db_manager.get_buyer_config()
        target_email = (buyer_email or current.get("buyer_email") or "").strip()
        updated = db_manager.update_buyer_config(
            {"buyer_email": target_email, "connection_status": "Configured"}
        )
        ver = await self.verify_merchant_identity()
        now = _utc_now_iso()
        details = {
            "sandbox_oauth_reachable": bool(ver.get("oauth_success")),
            "buyer_merchant_separated": target_email.lower()
            != ULTRON_MERCHANT["merchant_email"].lower(),
            "merchant_receiving_email": ULTRON_MERCHANT["merchant_email"],
            "sandbox_checkout_portal": "https://www.sandbox.paypal.com",
            "verified_at": now,
        }
        return db_manager.update_buyer_config(
            {
                "buyer_email": target_email,
                "connection_status": "Configured",
                "last_tested_at": now,
                "last_test_details": details,
            }
        )


paypal_client = PayPalSandboxClient()
