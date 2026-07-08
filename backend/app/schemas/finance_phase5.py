from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal

# --- AI Insights ---
class AIFinanceInsightBase(BaseModel):
    insight_type: str
    title: str
    description: str
    severity: str = "LOW"
    confidence_score: Decimal = Decimal("100.00")
    reference_id: Optional[str] = None
    status: str = "PENDING"

class AIFinanceInsightCreate(AIFinanceInsightBase):
    tenant_id: UUID

class AIFinanceInsightOut(AIFinanceInsightBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- AI Copilot Chat Logs ---
class AICopilotLogBase(BaseModel):
    prompt: str
    response: str
    context_used: Optional[str] = None

class AICopilotLogCreate(AICopilotLogBase):
    tenant_id: UUID
    user_id: UUID

class AICopilotLogOut(AICopilotLogBase):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- API Payloads ---
class AIChatRequest(BaseModel):
    prompt: str

class AIChatResponse(BaseModel):
    response: str
    confidence: float
