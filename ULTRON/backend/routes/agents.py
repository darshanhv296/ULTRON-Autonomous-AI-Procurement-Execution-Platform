"""
ULTRON Multi-Agent Execution, AI Telemetry & Assistant Routes (backend/routes/agents.py)
"""
from fastapi import APIRouter, HTTPException

from backend.database import db_manager
from backend.integrations.openrouter import openrouter_client
from backend.schemas import AssistantQueryRequest
from backend.services.execution_service import execution_service

router = APIRouter(prefix="/api", tags=["Multi-Agent Orchestration & AI"])


@router.get("/missions")
async def list_missions():
    return db_manager.state.get("missions", [])


@router.post("/missions/{mission_id}/replan")
async def replan_mission(mission_id: str):
    try:
        return execution_service.trigger_replan(mission_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/ai/runs")
@router.get("/ai-runs")
async def list_ai_runs():
    return db_manager.state.get("ai_runs", [])


@router.post("/ai/assistant")
@router.post("/assistant/query")
async def assistant_query(payload: AssistantQueryRequest):
    return await openrouter_client.chat_response(
        prompt=payload.prompt, objective_id=payload.objective_id
    )
