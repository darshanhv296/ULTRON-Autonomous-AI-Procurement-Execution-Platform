"""
ULTRON Researcher Agent (backend/agents/researcher.py)
Discovers real candidate products from Channel3 and verified catalog snapshots.
"""
from typing import Any, Dict, List

from backend.integrations.channel3 import channel3_client


class ResearcherAgent:
    """Autonomous Product Discovery & Market Research Agent."""

    async def discover_candidates(self, parsed_req: Dict[str, Any]) -> List[Dict[str, Any]]:
        direct_id = parsed_req.get("direct_product_id")
        if direct_id:
            exact = await channel3_client.search_products(query=direct_id)
            if exact:
                return exact

        category = parsed_req.get("category", "")
        cat_filter = "" if category == "hardware" else category
        candidates = await channel3_client.search_products(
            query="" if cat_filter else parsed_req.get("raw_prompt", ""),
            category=cat_filter,
        )
        if not candidates:
            candidates = await channel3_client.search_products()
        return candidates


researcher_agent = ResearcherAgent()
