"""
ULTRON PayPal Sandbox Payments, Verification & Buyer Config Routes (backend/routes/payments.py)
"""
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from backend.database import db_manager
from backend.integrations.paypal import paypal_client
from backend.schemas import (
    ApprovePaymentRequest,
    AutoCaptureRequest,
    BuyerConfigRequest,
    CleanupTestRecordsRequest,
    CreatePaymentRequest,
)

router = APIRouter(prefix="/api", tags=["PayPal Sandbox Payments"])


@router.get("/payments")
async def list_payments():
    return db_manager.get_payment_orders()


@router.get("/payments/cleanup-test-records/preview")
@router.get("/admin/cleanup-test-records/preview")
async def preview_cleanup_test_records():
    return db_manager.preview_test_records_cleanup()


@router.post("/payments/cleanup-test-records")
@router.post("/admin/cleanup-test-records")
async def execute_cleanup_test_records(payload: CleanupTestRecordsRequest):
    try:
        return db_manager.execute_test_records_cleanup(
            admin_email=payload.admin_email or "demo@example.invalid",
            confirmation_phrase=payload.confirmation_phrase,
            final_confirmed=payload.final_confirmed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    order = db_manager.get_payment_order_by_id(payment_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Payment order {payment_id} not found")
    return order


@router.post("/payments/create", status_code=201)
async def create_payment_order(payload: CreatePaymentRequest, request: Request):
    proto = request.headers.get("x-forwarded-proto", request.url.scheme or "http").split(",")[0].strip()
    host = request.headers.get("host", "127.0.0.1:8000")
    app_base_url = f"{proto}://{host}"
    try:
        return await paypal_client.create_sandbox_order(
            plan_id=payload.plan_id,
            approval_id=payload.approval_id,
            app_base_url=app_base_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/payments/callback/return")
async def paypal_return_callback(token: str = "", PayerID: str = ""):
    if not token:
        return RedirectResponse(url="/?paypal_return=error&reason=missing_token")
    try:
        auto_res = await paypal_client.auto_verify_and_capture_on_return(token, PayerID)
        ord_rec = auto_res["order"]
        return_state = "completed" if ord_rec.get("status") == "COMPLETED" else "approved"
        cap_param = (
            f"&capture_id={quote(str(ord_rec['capture_id']))}"
            if ord_rec.get("capture_id")
            else ""
        )
        target_url = (
            f"/?paypal_return={return_state}"
            f"&token={quote(token)}"
            f"&PayerID={quote(PayerID)}"
            f"&payment_id={quote(str(ord_rec['id']))}"
            f"&paypal_status={quote(str(auto_res['paypal_status']))}"
            f"&payment_stage={quote(str(auto_res['payment_stage']))}"
            f"{cap_param}"
        )
        return RedirectResponse(url=target_url)
    except Exception as exc:
        return RedirectResponse(
            url=f"/?paypal_return=error&token={quote(token)}&reason={quote(str(exc))}"
        )


@router.get("/payments/callback/cancel")
async def paypal_cancel_callback(token: str = ""):
    return RedirectResponse(url=f"/?paypal_return=cancelled&token={quote(token)}")


@router.post("/payments/{payment_id}/verify-paypal")
async def verify_paypal_order(payment_id: str):
    try:
        return await paypal_client.verify_and_sync_order(payment_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/payments/{payment_id}/auto-capture")
async def auto_capture_order(payment_id: str, payload: AutoCaptureRequest):
    try:
        payer_id = payload.payer_id or payload.PayerID or ""
        return await paypal_client.auto_verify_and_capture_on_return(payment_id, payer_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/payments/{payment_id}/approve")
async def approve_payment_order(payment_id: str, _payload: ApprovePaymentRequest):
    try:
        return await paypal_client.verify_and_sync_order(payment_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/payments/{payment_id}/capture")
async def capture_payment_order(payment_id: str):
    try:
        return await paypal_client.capture_sandbox_order(payment_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/payments/{payment_id}/refund-eligibility")
async def check_refund_eligibility(payment_id: str):
    order = db_manager.get_payment_order_by_id(payment_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    eligible = order.get("status") == "COMPLETED" and order.get("id") != "REDACTED_TEST_REFERENCE"
    return {"payment_id": order["id"], "eligible": eligible, "status": order.get("status")}


@router.get("/paypal/merchant-verification")
async def get_merchant_verification():
    return await paypal_client.verify_merchant_identity(force_refresh=False)


@router.post("/paypal/merchant-verification/reload")
async def reload_merchant_verification():
    return await paypal_client.verify_merchant_identity(force_refresh=True)


@router.get("/paypal/buyer-config")
async def get_buyer_config():
    return db_manager.get_buyer_config()


@router.post("/paypal/buyer-config")
async def save_buyer_config(payload: BuyerConfigRequest):
    try:
        return db_manager.update_buyer_config(
            {"buyer_email": payload.buyer_email, "connection_status": "Configured"}
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/paypal/buyer-config/test")
async def test_buyer_config(payload: BuyerConfigRequest):
    try:
        return await paypal_client.test_buyer_configuration(payload.buyer_email)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
