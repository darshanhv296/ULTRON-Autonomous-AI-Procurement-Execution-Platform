"""
ULTRON Procurement Agent (backend/agents/procurement_agent.py)
Evaluates candidate products against budget & technical constraints, scores & ranks them,
and builds the structured comparison matrix.
"""
from typing import Any, Dict, List


class ProcurementAgent:
    """Autonomous Product Evaluation, Ranking & Selection Agent."""

    def evaluate_and_rank(
        self, candidates: List[Dict[str, Any]], parsed_req: Dict[str, Any]
    ) -> Dict[str, Any]:
        budget_usd = parsed_req.get("budget_usd")
        qty = max(1, int(parsed_req.get("quantity", 1)))
        per_unit_budget = None
        if budget_usd is not None:
            # Handle both per-unit ("under $100 each") and total budget
            if "each" in parsed_req.get("raw_prompt", "").lower() or qty == 1:
                per_unit_budget = budget_usd
            else:
                per_unit_budget = round(budget_usd / qty, 2)

        evaluated: List[Dict[str, Any]] = []
        for item in candidates:
            price = float(item.get("price", 0.0))
            rating = float(item.get("rating", 4.5))
            in_stock = bool(item.get("in_stock", True))

            within_budget = True
            if per_unit_budget is not None and price > per_unit_budget:
                within_budget = False

            # Calculate deterministic multi-criteria score (0 - 100)
            score = 70.0 + (rating * 4.5)
            if within_budget:
                score += 8.0
            else:
                score -= 20.0
            if in_stock:
                score += 4.0

            enriched = dict(item)
            enriched["within_budget"] = within_budget
            enriched["score"] = round(min(99.5, max(10.0, score)), 1)
            enriched["total_for_quantity"] = round(price * qty, 2)
            evaluated.append(enriched)

        evaluated.sort(
            key=lambda x: (x.get("within_budget", True), x.get("score", 0), -x.get("price", 0)),
            reverse=True,
        )

        top_rec = evaluated[0] if evaluated else None
        return {
            "ranked_candidates": evaluated,
            "top_recommendation": top_rec,
            "within_budget_count": sum(1 for c in evaluated if c.get("within_budget")),
        }


procurement_agent = ProcurementAgent()
