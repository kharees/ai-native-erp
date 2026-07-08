from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta

# Risk Score
class AICreditRiskScoreResponse(BaseModel):
    customer_id: uuid.UUID
    risk_score: int = Field(..., description="0 to 100 score. Higher is riskier.")
    risk_category: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    delay_probability_percent: float
    recommended_credit_limit: float
    factors: list[str]

# Smart Draft
class AISmartDraftRequest(BaseModel):
    customer_id: uuid.UUID
    partial_items: list[dict]

class AISmartDraftResponse(BaseModel):
    suggested_products: list[dict]
    suggested_discounts: list[dict]
    hsn_sac_recommendations: dict
    confidence_score: float

# Fraud Alert
class AIFraudAlertBase(BaseModel):
    customer_id: uuid.UUID | None = None
    invoice_id: uuid.UUID | None = None
    alert_type: str = Field(..., max_length=64)
    severity: str = Field(..., max_length=32)
    alert_details: str
    status: str = Field("OPEN", max_length=32)

class AIFraudAlertResponse(AIFraudAlertBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
