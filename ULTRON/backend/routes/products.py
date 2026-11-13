"""
ULTRON Product Discovery, Comparison & Cart Routes (backend/routes/products.py)
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.database import db_manager
from backend.integrations.channel3 import channel3_client
from backend.schemas import (
    CartCheckoutRequest,
    CartItemAddRequest,
    CartItemQuantityRequest,
    ProductCompareRequest,
)
from backend.services.procurement_service import procurement_service

router = APIRouter(prefix="/api", tags=["Product Discovery & Cart"])


def _compute_cart_response() -> Dict[str, Any]:
    items = db_manager.state.get("cart", [])
    subtotal = round(
        sum(float(i.get("unit_price", 0)) * int(i.get("quantity", 1)) for i in items), 2
    )
    tax = round(subtotal * 0.0825, 2)
    shipping = 0.0 if subtotal == 0 or subtotal >= 150.0 else 14.99
    total = round(subtotal + tax + shipping, 2)
    return {
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "currency": "USD",
    }


@router.get("/products/search")
async def search_products(
    q: str = Query(default=""),
    category: str = Query(default=""),
    max_price: Optional[float] = Query(default=None),
):
    return await channel3_client.search_products(
        query=q, category=category, max_price=max_price
    )


@router.get("/products/snapshots")
async def list_product_snapshots():
    return db_manager.state.get("product_snapshots", [])


@router.post("/products/compare")
async def compare_products(payload: ProductCompareRequest):
    return procurement_service.compare_products(payload.product_ids)


@router.get("/cart")
async def get_cart():
    return _compute_cart_response()


@router.post("/cart/items")
async def add_to_cart(payload: CartItemAddRequest):
    snapshots = db_manager.state.get("product_snapshots", [])
    product = next(
        (
            s
            for s in snapshots
            if s.get("id") == payload.product_id or s.get("external_id") == payload.product_id
        ),
        None,
    )
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {payload.product_id} not found")

    cart: List[Dict[str, Any]] = db_manager.state.setdefault("cart", [])
    existing = next((c for c in cart if c.get("product_id") == product["id"]), None)
    if existing:
        existing["quantity"] = int(existing.get("quantity", 1)) + payload.quantity
    else:
        cart.append(
            {
                "product_id": product["id"],
                "external_id": product.get("external_id"),
                "title": product["title"],
                "vendor": product.get("vendor", "Channel3 Verified Vendor"),
                "unit_price": float(product["price"]),
                "quantity": payload.quantity,
                "image_url": product.get("image_url", ""),
                "category": product.get("category", "hardware"),
            }
        )
    db_manager.save_state()
    return _compute_cart_response()


@router.patch("/cart/items/{product_id}")
@router.put("/cart/items/{product_id}")
async def update_cart_item_quantity(product_id: str, payload: CartItemQuantityRequest):
    cart: List[Dict[str, Any]] = db_manager.state.setdefault("cart", [])
    target = next(
        (
            c
            for c in cart
            if c.get("product_id") == product_id or c.get("external_id") == product_id
        ),
        None,
    )
    if not target:
        raise HTTPException(status_code=404, detail=f"Cart item {product_id} not found")

    if payload.quantity <= 0:
        db_manager.state["cart"] = [
            c for c in cart if c.get("product_id") != target.get("product_id")
        ]
    else:
        target["quantity"] = payload.quantity

    db_manager.save_state()
    return _compute_cart_response()


@router.delete("/cart/items/{product_id}")
async def remove_from_cart(product_id: str):
    cart: List[Dict[str, Any]] = db_manager.state.setdefault("cart", [])
    db_manager.state["cart"] = [
        c
        for c in cart
        if c.get("product_id") != product_id and c.get("external_id") != product_id
    ]
    db_manager.save_state()
    return _compute_cart_response()


@router.delete("/cart")
async def clear_cart():
    db_manager.state["cart"] = []
    db_manager.save_state()
    return _compute_cart_response()


@router.post("/cart/checkout", status_code=201)
async def checkout_cart_to_plan(payload: CartCheckoutRequest):
    cart_summary = _compute_cart_response()
    if not cart_summary["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    obj = db_manager.create_objective(
        title=payload.title or f"Cart Procurement ({len(cart_summary['items'])} items)",
        description=payload.notes
        or "Generated from ULTRON Cart & Procurement Builder.",
        budget_limit=payload.budget_limit or cart_summary["total"],
        currency="USD",
    )

    items_input = [
        {
            "product_snapshot_id": it["product_id"],
            "title": it["title"],
            "unit_price": it["unit_price"],
            "quantity": it["quantity"],
        }
        for it in cart_summary["items"]
    ]
    plan = db_manager.create_plan(
        objective_id=obj["id"],
        notes=payload.notes or f"Cart checkout plan (${cart_summary['total']:.2f} USD).",
        items_input=items_input,
    )
    db_manager.state["cart"] = []
    db_manager.save_state()
    return {"objective": obj, "plan": plan}
