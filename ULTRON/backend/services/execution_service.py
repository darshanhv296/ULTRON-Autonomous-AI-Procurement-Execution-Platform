"""
ULTRON Execution Service (backend/services/execution_service.py)
Manages multi-agent mission execution, stage progression, and dynamic replanning.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict

from backend.database import db_manager
from backend.services.procurement_service import procurement_service


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ExecutionService:
    """Multi-Agent Workflow Execution & Replanning Service."""

    async def execute_objective(self, objective_id: str) -> Dict[str, Any]:
        obj = db_manager.get_objective_by_id(objective_id)
        if not obj:
            raise ValueError(f"Objective {objective_id} not found.")

        res = await procurement_service.run_natural_language_pipeline(
            prompt=f"{obj['title']}. {obj['description']}",
            auto_prepare_order=True,
        )
        return res

    def trigger_replan(self, mission_id: str) -> Dict[str, Any]:
        now = _utc_now_iso()
        target = None
        for m in db_manager.state.get("missions", []):
            if m.get("id") == mission_id:
                target = m
                break
        if not target:
            raise ValueError(f"Mission {mission_id} not found.")

        target["status"] = "REPLANNING"
        target["current_stage"] = "Dynamic Recovery & Vendor Re-Sourcing"
        target["agent_assigned"] = "ULTRON Planner & Recovery Agent"

        db_manager.log_event(
            target.get("objective_id", "OBJ-1001"),
            "MISSION_REPLANNED",
            "ULTRON Recovery Agent",
            f"Mission {mission_id} triggered dynamic replanning and vendor re-evaluation.",
            {"mission_id": mission_id, "replanned_at": now},
        )
        db_manager.save_state()
        return target


execution_service = ExecutionService()
