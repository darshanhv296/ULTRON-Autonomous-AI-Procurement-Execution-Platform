"""
ULTRON Payment Agent (backend/agents/payment_agent.py)
Coordinates payment readiness verification, PayPal Sandbox order creation,
and live settlement tracking.
"""
from typing import Any, Dict, Optional

from backend.integrations.paypal import paypal_client


class PaymentAgent:
    """Autonomous Financial Settlement & PayPal Sandbox Execution Agent."""

    async def initiate_checkout(
        self, plan_id: str, approval_id: Optional[str], app_base_url: str
    ) -> Dict[str, Any]:
        return await paypal_client.create_sandbox_order(
            plan_id=plan_id, approval_id=approval_id, app_base_url=app_base_url
        )

    async def verify_order(self, payment_id_or_token: str) -> Dict[str, Any]:
        return await paypal_client.verify_and_sync_order(payment_id_or_token)

    async def capture_order(self, payment_id_or_token: str) -> Dict[str, Any]:
        return await paypal_client.capture_sandbox_order(payment_id_or_token)


payment_agent = PaymentAgent()
