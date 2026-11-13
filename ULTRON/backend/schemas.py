"""
ULTRON Pydantic v2 Request and Response Schemas
Validates all incoming API payloads and structures API responses.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateObjectiveRequest(BaseModel):
    title: str = Field(..., min_length=2)
    description: str = Field(..., min_length=2)
    budget_limit: Optional[float] = None
    currency: str = "USD"
    constraints: Optional[List[Dict[str, Any]]] = None
    auto_execute: bool = False


class NaturalLanguageProcurementRequest(BaseModel):
    prompt: str = Field(..., min_length=2)
    auto_prepare_order: bool = True


class ProductCompareRequest(BaseModel):
    product_ids: List[str] = Field(..., min_length=2)


class CartItemAddRequest(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)


class CartItemQuantityRequest(BaseModel):
    quantity: int = Field(..., ge=0)


class CartCheckoutRequest(BaseModel):
    title: Optional[str] = None
    budget_limit: Optional[float] = None
    notes: Optional[str] = None


class CreatePlanItemInput(BaseModel):
    product_snapshot_id: str
    title: Optional[str] = None
    unit_price: Optional[float] = None
    quantity: int = Field(default=1, ge=1)


class CreatePlanRequest(BaseModel):
    objective_id: str
    notes: Optional[str] = None
    items: List[CreatePlanItemInput]


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    comments: Optional[str] = None


class CreatePaymentRequest(BaseModel):
    plan_id: str
    approval_id: Optional[str] = None


class ApprovePaymentRequest(BaseModel):
    buyer_email: Optional[str] = None


class AutoCaptureRequest(BaseModel):
    payer_id: Optional[str] = None
    PayerID: Optional[str] = None


class BuyerConfigRequest(BaseModel):
    buyer_email: str


class CleanupTestRecordsRequest(BaseModel):
    admin_email: Optional[str] = "demo@example.invalid"
    confirmation_phrase: str
    final_confirmed: bool = False


class CancelOrderRequest(BaseModel):
    reason: Optional[str] = "Cancelled by administrator"


class AssistantQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    objective_id: Optional[str] = None
