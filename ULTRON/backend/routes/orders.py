"""
ULTRON Orders, Fulfillment Tracking & Cancellation Routes (backend/routes/orders.py)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from backend.database import PROTECTED_PAYMENT_ID, db_manager
from backend.schemas import CancelOrderRequest

router = APIRouter(prefix="/api", tags=["Orders & Lifecycle Tracking"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/orders")
async def list_orders():
    return db_manager.get_payment_orders()


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    ord_rec = db_manager.get_payment_order_by_id(order_id)
    if not ord_rec:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return ord_rec


@router.post("/orders/{order_id}/refresh-tracking")
async def refresh_order_tracking(order_id: str):
    ord_rec = db_manager.get_payment_order_by_id(order_id)
    if not ord_rec:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    now = _utc_now_iso()
    meta = ord_rec.setdefault("payment_metadata", {})
    shipping = meta.setdefault("shipping_and_tracking", {})
    shipping["last_verified_at"] = now
    if ord_rec.get("status") == "COMPLETED":
        shipping["carrier"] = shipping.get("carrier") or "FedEx Ground Delivery"
        shipping["tracking_number"] = (
            shipping.get("tracking_number") or f"FX-TRK-{ord_rec['id'][-6:]}"
        )
        shipping["shipment_status"] = shipping.get("shipment_status") or "IN_TRANSIT"
        shipping["estimated_delivery"] = (
            shipping.get("estimated_delivery") or "Estimated 2-3 Business Days"
        )
    else:
        shipping["shipment_status"] = "AWAITING_PAYMENT_SETTLEMENT"

    ord_rec["updated_at"] = now
    db_manager.save_state()
    return ord_rec


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, payload: CancelOrderRequest):
    ord_rec = db_manager.get_payment_order_by_id(order_id)
    if not ord_rec:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if ord_rec.get("id") == PROTECTED_PAYMENT_ID:
        raise HTTPException(
            status_code=403,
            detail="FORBIDDEN: Historical protected $899.79 transaction cannot be cancelled or modified.",
        )

    now = _utc_now_iso()
    meta = ord_rec.setdefault("payment_metadata", {})
    if ord_rec.get("status") == "COMPLETED":
        ord_rec["status"] = "REFUNDED"
        meta["cancellation_and_refund"] = {
            "cancellation_status": "REFUNDED",
            "cancellation_reason": payload.reason,
            "cancelled_at": now,
            "refund_amount": ord_rec.get("amount", 0.0),
        }
    else:
        ord_rec["status"] = "CANCELLED"
        meta["cancellation_and_refund"] = {
            "cancellation_status": "CANCELLED",
            "cancellation_reason": payload.reason,
            "cancelled_at": now,
            "refund_amount": 0.0,
        }
    ord_rec["updated_at"] = now
    db_manager.save_state()
    return ord_rec
