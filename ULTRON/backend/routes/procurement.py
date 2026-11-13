"""
ULTRON Procurement, Objectives, Plans, Approvals & Dashboard Routes
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from backend.database import db_manager
from backend.schemas import (
    ApprovalDecisionRequest,
    CreateObjectiveRequest,
    CreatePlanRequest,
    NaturalLanguageProcurementRequest,
)
from backend.services.approval_service import approval_service
from backend.services.execution_service import execution_service
from backend.services.procurement_service import procurement_service

router = APIRouter(prefix="/api", tags=["Procurement & Governance"])


@router.get("/dashboard/metrics")
async def get_dashboard_metrics():
    return db_manager.get_dashboard_metrics()


@router.get("/objectives")
async def list_objectives():
    return db_manager.get_objectives()


@router.get("/objectives/{objective_id}")
async def get_objective(objective_id: str):
    obj = db_manager.get_objective_by_id(objective_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Objective {objective_id} not found")
    return obj


@router.post("/objectives", status_code=201)
async def create_objective(payload: CreateObjectiveRequest):
    obj = db_manager.create_objective(
        title=payload.title,
        description=payload.description,
        budget_limit=payload.budget_limit,
        currency=payload.currency,
        constraints=payload.constraints,
    )
    if payload.auto_execute:
        exec_res = await execution_service.execute_objective(obj["id"])
        return {"objective": obj, "execution": exec_res}
    return obj


@router.post("/objectives/{objective_id}/execute")
async def execute_objective(objective_id: str):
    try:
        return await execution_service.execute_objective(objective_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/procurement/natural-language")
async def natural_language_procurement(payload: NaturalLanguageProcurementRequest):
    try:
        return await procurement_service.run_natural_language_pipeline(
            prompt=payload.prompt,
            auto_prepare_order=payload.auto_prepare_order,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/plans")
async def list_plans():
    return db_manager.get_plans()


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    pl = db_manager.get_plan_by_id(plan_id)
    if not pl:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return pl


@router.post("/plans", status_code=201)
async def create_plan(payload: CreatePlanRequest):
    items_input = [it.model_dump() for it in payload.items]
    return db_manager.create_plan(
        objective_id=payload.objective_id,
        notes=payload.notes or "",
        items_input=items_input,
    )


@router.get("/approvals")
async def list_approvals():
    return approval_service.list_approvals()


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(approval_id: str, payload: ApprovalDecisionRequest):
    try:
        return approval_service.process_decision(
            approval_id=approval_id,
            decision=payload.decision,
            comments=payload.comments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/audit/events")
@router.get("/audit-events")
async def list_audit_events(objective_id: Optional[str] = Query(default=None)):
    events = db_manager.state.get("objective_events", [])
    if objective_id:
        events = [e for e in events if e.get("objective_id") == objective_id]
    return events


@router.get("/notifications")
async def get_notifications():
    events = db_manager.state.get("objective_events", [])[:8]
    return [
        {
            "id": ev.get("id"),
            "title": ev.get("event_type"),
            "message": ev.get("message"),
            "created_at": ev.get("created_at"),
        }
        for ev in events
    ]


@router.get("/search")
async def global_search(q: str = Query(default="")):
    q_low = q.strip().lower()
    if not q_low:
        return {"objectives": [], "products": [], "plans": [], "payments": []}
    return {
        "objectives": [
            o
            for o in db_manager.get_objectives()
            if q_low in str(o.get("id", "")).lower() or q_low in str(o.get("title", "")).lower()
        ],
        "products": [
            p
            for p in db_manager.state.get("product_snapshots", [])
            if q_low in str(p.get("title", "")).lower()
            or q_low in str(p.get("external_id", "")).lower()
        ],
        "plans": [
            pl
            for pl in db_manager.get_plans()
            if q_low in str(pl.get("id", "")).lower() or q_low in str(pl.get("notes", "")).lower()
        ],
        "payments": [
            pay
            for pay in db_manager.get_payment_orders()
            if q_low in str(pay.get("id", "")).lower()
            or q_low in str(pay.get("paypal_order_id", "")).lower()
        ],
    }
