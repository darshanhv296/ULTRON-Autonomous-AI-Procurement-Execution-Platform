"""
ULTRON Channel3 Product Discovery Integration Module
Queries live Channel3 API when CHANNEL3_API_KEY is configured and merges with
verified enterprise hardware snapshots.
"""
from typing import Any, Dict, List, Optional
import httpx

from backend.config import settings
from backend.database import db_manager


class Channel3Client:
    """Modular Channel3 Product Discovery Client."""

    async def search_products(
        self,
        query: str = "",
        category: str = "",
        max_price: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        # 1. Query external Channel3 API if configured
        if settings.is_channel3_configured:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    params: Dict[str, Any] = {}
                    if query:
                        params["q"] = query
                    if category:
                        params["category"] = category
                    if max_price is not None:
                        params["max_price"] = max_price
                    resp = await client.get(
                        f"{settings.CHANNEL3_API_URL.rstrip('/')}/products",
                        headers={"Authorization": f"Bearer {settings.CHANNEL3_API_KEY}"},
                        params=params,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data if isinstance(data, list) else data.get("products", [])
                        for it in items:
                            results.append(it)
            except Exception:
                pass

        # 2. Search verified snapshots in database
        snapshots = db_manager.state.get("product_snapshots", [])
        q_lower = (query or "").strip().lower()
        cat_lower = (category or "").strip().lower()

        # Check direct SKU / Product ID lookup first
        for snap in snapshots:
            ext_id = str(snap.get("external_id", "")).lower()
            snap_id = str(snap.get("id", "")).lower()
            sku = str((snap.get("specs_json") or {}).get("sku", "")).lower()
            if q_lower and (q_lower in (ext_id, snap_id, sku) or ext_id in q_lower or sku in q_lower):
                if snap not in results:
                    results.append(snap)

        for snap in snapshots:
            if snap in results:
                continue
            if cat_lower and snap.get("category", "").lower() != cat_lower:
                continue
            if max_price is not None and float(snap.get("price", 0)) > max_price:
                continue
            if q_lower:
                haystack = " ".join(
                    [
                        str(snap.get("title", "")),
                        str(snap.get("description", "")),
                        str(snap.get("category", "")),
                        str(snap.get("vendor", "")),
                        str(snap.get("external_id", "")),
                        str(snap.get("specs_json", {})),
                    ]
                ).lower()
                tokens = [
                    t
                    for t in q_lower.replace(",", " ").split()
                    if len(t) > 2 and t not in ("find", "under", "with", "and", "the", "for", "purchase")
                ]
                if tokens and not any(tok in haystack for tok in tokens):
                    continue
            results.append(snap)

        return results


channel3_client = Channel3Client()
