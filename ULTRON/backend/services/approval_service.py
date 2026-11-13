"""
ULTRON Approval Service (backend/services/approval_service.py)
Enforces human governance checkpoints before PayPal Sandbox order creation.
"""
from typing import Any, Dict, List, Optional

from backend.database import db_manager


class ApprovalService:
    """Financial Governance & Human Checkpoint Service."""

    def list_approvals(self) -> List[Dict[str, Any]]:
        return db_manager.get_approvals()

    def process_decision(
        self, approval_id: str, decision: str, comments: Optional[str] = None
    ) -> Dict[str, Any]:
        if decision not in ("APPROVED", "REJECTED"):
            raise ValueError("Decision must be APPROVED or REJECTED.")
        return db_manager.decide_approval(approval_id, decision, comments)


approval_service = ApprovalService()
