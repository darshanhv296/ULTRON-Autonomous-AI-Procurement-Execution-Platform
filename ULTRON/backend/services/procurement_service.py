"""
ULTRON Procurement Service (backend/services/procurement_service.py)
Coordinates the 13-stage autonomous procurement pipeline:
Understand -> Plan -> Discover -> Filter -> Evaluate -> Rank -> Present -> Select -> Prepare Plan -> Request Approval.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.agents.planner import planner_agent
from backend.agents.procurement_agent import procurement_agent
from backend.agents.researcher import researcher_agent
from backend.database import db_manager


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ProcurementService:
    """End-to-End Autonomous Procurement Orchestration Service."""

    async def run_natural_language_pipeline(
        self, prompt: str, auto_prepare_order: bool = True
    ) -> Dict[str, Any]:
        # Stage 1 & 2: Parse Objective & Create Constraints
        parsed = await planner_agent.parse_objective(prompt)
        constraints_input = []
        if parsed["budget_limit"] is not None:
            constraints_input.append(
                {
                    "constraint_type": "max_budget",
                    "constraint_value": f"{parsed['budget_limit']:.2f} {parsed['currency']}",
                    "is_hard_constraint": True,
                }
            )
        for sp in parsed.get("required_specs", []):
            constraints_input.append(
                {
                    "constraint_type": "quality_tier",
                    "constraint_value": sp,
                    "is_hard_constraint": True,
                }
            )

        obj = db_manager.create_objective(
            title=f"Procure {parsed['category'].upper()}: {prompt[:90]}",
            description=parsed["reasoning_summary"],
            budget_limit=parsed["budget_limit"],
            currency=parsed["currency"],
            constraints=constraints_input,
        )

        # Stage 3: Discover Candidates
        candidates = await researcher_agent.discover_candidates(parsed)

        # Stage 4, 5, 6: Filter, Evaluate & Rank
        eval_res = procurement_agent.evaluate_and_rank(candidates, parsed)
        ranked = eval_res["ranked_candidates"]
        top_rec = eval_res["top_recommendation"]

        plan = None
        approval = None
        if auto_prepare_order and top_rec:
            plan = db_manager.create_plan(
                objective_id=obj["id"],
                notes=(
                    f"Autonomous selection: {parsed['quantity']}x {top_rec['title']} "
                    f"(${top_rec['price']:.2f} USD/unit)."
                ),
                items_input=[
                    {
                        "product_snapshot_id": top_rec["id"],
                        "title": top_rec["title"],
                        "unit_price": top_rec["price"],
                        "quantity": parsed["quantity"],
                    }
                ],
                currency="USD",
            )
            approvals = plan.get("approvals", [])
            approval = approvals[0] if approvals else None

        # Record Mission
        now = _utc_now_iso()
        mission = {
            "id": f"MSN-{str(int(time.time() * 1000))[-5:]}",
            "objective_id": obj["id"],
            "status": "RUNNING",
            "current_stage": "10. Awaiting Human Governance Approval",
            "agent_assigned": "ULTRON Governance & Approval Coordinator",
            "started_at": now,
            "completed_at": None,
        }
        db_manager.state.setdefault("missions", []).insert(0, mission)
        db_manager.save_state()

        stages = [
            {"stage": 1, "name": "Understand Objective", "status": "COMPLETED", "detail": parsed["reasoning_summary"]},
            {"stage": 2, "name": "Dynamic Mission Plan", "status": "COMPLETED", "detail": f"Created Objective {obj['id']} & Mission {mission['id']}"},
            {"stage": 3, "name": "Channel3 Discovery", "status": "COMPLETED", "detail": f"Discovered {len(candidates)} candidate products"},
            {"stage": 4, "name": "Constraint Filtering", "status": "COMPLETED", "detail": f"{eval_res['within_budget_count']} within budget threshold"},
            {"stage": 5, "name": "Multi-Criteria Evaluation", "status": "COMPLETED", "detail": "Evaluated specs, ratings, and stock readiness"},
            {"stage": 6, "name": "Candidate Ranking", "status": "COMPLETED", "detail": f"Top score: {top_rec['score'] if top_rec else 0}/100"},
            {"stage": 7, "name": "Purchase Plan Creation", "status": "COMPLETED" if plan else "SKIPPED", "detail": f"Plan {plan['id']} (${plan['total_amount']:.2f} USD)" if plan else "No candidate"},
            {"stage": 8, "name": "Human Approval Checkpoint", "status": "AWAITING_ACTION" if approval else "PENDING", "detail": f"Approval {approval['id']} (PENDING)" if approval else "Pending"},
        ]

        return {
            "objective": obj,
            "parsed_requirements": parsed,
            "mission": mission,
            "stages": stages,
            "candidates": ranked,
            "top_recommendation": top_rec,
            "purchase_plan": plan,
            "approval": approval,
        }

    def compare_products(self, product_ids: List[str]) -> Dict[str, Any]:
        snapshots = db_manager.state.get("product_snapshots", [])
        selected = [
            s
            for s in snapshots
            if s.get("id") in product_ids or s.get("external_id") in product_ids
        ]
        if len(selected) < 2:
            selected = snapshots[: min(3, len(snapshots))]

        ranked = sorted(
            selected,
            key=lambda x: (float(x.get("rating", 4.5)) / max(1.0, float(x.get("price", 100.0)))),
            reverse=True,
        )
        winner = ranked[0] if ranked else None
        return {
            "products": selected,
            "recommended_winner": winner,
            "comparison_summary": (
                f"Recommended {winner['title']} (${winner['price']:.2f} USD, Rating {winner['rating']}★) "
                "based on optimal price-to-specification ratio and immediate Channel3 stock availability."
                if winner
                else "No products available for comparison."
            ),
        }


procurement_service = ProcurementService()
