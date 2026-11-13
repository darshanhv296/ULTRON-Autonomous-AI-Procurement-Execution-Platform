"""
ULTRON Planner Agent (backend/agents/planner.py)
Parses natural language procurement requests into structured requirements, constraints,
and dynamic execution plans. Uses deterministic Python parsing first, augmented by
OpenRouter / Groq LLM reasoning when needed.
"""
import re
from typing import Any, Dict, List, Optional

from backend.integrations.openrouter import openrouter_client

WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


class PlannerAgent:
    """Autonomous Requirement Understanding & Mission Planner Agent."""

    async def parse_objective(self, prompt: str) -> Dict[str, Any]:
        clean = prompt.strip()
        lower = clean.lower()

        # 1. Detect Direct Product ID / SKU Lookup
        sku_match = re.search(
            r"(?:product\s*id|sku|item\s*id)\s*[:=#]?\s*([A-Za-z0-9_-]+)", clean, re.I
        )
        direct_sku: Optional[str] = sku_match.group(1) if sku_match else None

        # 2. Detect Currency & Budget
        currency = "USD"
        if "₹" in clean or "inr" in lower or "rupee" in lower:
            currency = "INR"
        elif "€" in clean or "eur" in lower:
            currency = "EUR"
        elif "£" in clean or "gbp" in lower:
            currency = "GBP"

        budget_limit: Optional[float] = None
        budget_match = re.search(
            r"(?:under|below|max|within|budget(?:\s*of)?)\s*(?:[\$₹€£]|usd|inr|eur|gbp)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            clean,
            re.I,
        )
        if budget_match:
            budget_limit = float(budget_match.group(1).replace(",", ""))

        # 3. Detect Quantity
        quantity = 1
        qty_match = re.search(
            r"\b(\d+)\s*x?\s*(?:laptops?|monitors?|chairs?|gpus?|smartphones?|phones?|units?)\b",
            lower,
        )
        if qty_match:
            quantity = max(1, int(qty_match.group(1)))
        else:
            for word, num in WORD_NUMBERS.items():
                if re.search(rf"\b{word}\b", lower):
                    quantity = num
                    break

        # 4. Detect Category
        category = "hardware"
        if "laptop" in lower or "notebook" in lower or "ultrabook" in lower:
            category = "laptop"
        elif "monitor" in lower or "display" in lower or "144hz" in lower or "165hz" in lower:
            category = "monitor"
        elif "gpu" in lower or "graphics" in lower or "vram" in lower or "rtx" in lower:
            category = "gpu"
        elif "chair" in lower or "desk" in lower or "ergonomic" in lower:
            category = "chair"
        elif "phone" in lower or "smartphone" in lower or "mobile" in lower:
            category = "smartphone"

        # 5. Extract Technical Specification Constraints
        required_specs: List[str] = []
        ram_match = re.search(r"(\d+\s*gb)\s*ram", lower)
        if ram_match:
            required_specs.append(f"Minimum {ram_match.group(1).upper()} RAM")
        vram_match = re.search(r"(\d+\s*gb)\s*vram", lower)
        if vram_match:
            required_specs.append(f"Minimum {vram_match.group(1).upper()} VRAM")
        if "ssd" in lower or "nvme" in lower:
            required_specs.append("Solid State Drive (SSD/NVMe) Required")
        hz_match = re.search(r"(\d+\s*hz)", lower)
        if hz_match:
            required_specs.append(f"Minimum {hz_match.group(1)} Refresh Rate")
        storage_match = re.search(r"(\d+\s*(?:gb|tb))\s*(?:storage|ssd|nvme)?", lower)
        if storage_match and not ram_match and not vram_match:
            required_specs.append(f"Minimum {storage_match.group(1).upper()} Storage")

        # 6. Augment with OpenRouter / Groq if configured for ambiguous prompts
        llm_data = await openrouter_client.complete_json(
            system_prompt=(
                "You are the ULTRON Procurement Planner Agent. Return ONLY a JSON object with keys: "
                "category (string), quantity (number), budget_limit (number or null), currency (string), "
                "required_specs (array of strings), reasoning_summary (string)."
            ),
            user_prompt=f"Parse procurement objective: {clean}",
            agent_role="ULTRON Planner Agent",
        )

        reasoning_summary = (
            llm_data.get("reasoning_summary")
            if isinstance(llm_data, dict) and llm_data.get("reasoning_summary")
            else f"Parsed {category.upper()} procurement request (Qty: {quantity}, Budget: {budget_limit if budget_limit is not None else 'Open'} {currency})."
        )

        # Convert INR budget to USD equivalent for USD catalog matching if needed
        budget_usd: Optional[float] = None
        if budget_limit is not None:
            if currency == "INR":
                budget_usd = round(budget_limit / 83.5, 2)
            elif currency == "EUR":
                budget_usd = round(budget_limit * 1.08, 2)
            elif currency == "GBP":
                budget_usd = round(budget_limit * 1.27, 2)
            else:
                budget_usd = budget_limit

        return {
            "raw_prompt": clean,
            "direct_product_id": direct_sku,
            "category": category,
            "quantity": quantity,
            "budget_limit": budget_limit,
            "budget_usd": budget_usd,
            "currency": currency,
            "required_specs": required_specs,
            "reasoning_summary": reasoning_summary,
        }


planner_agent = PlannerAgent()
