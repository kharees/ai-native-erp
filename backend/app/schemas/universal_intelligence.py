import uuid
from pydantic import BaseModel, Field

class InventoryForecast(BaseModel):
    item_id: uuid.UUID
    item_name: str
    current_stock: float
    projected_demand_30d: float
    confidence_score: float = Field(..., ge=0, le=1)
    seasonality_trend: str # 'Increasing', 'Stable', 'Decreasing'

class OptimizationRecommendation(BaseModel):
    item_id: uuid.UUID
    item_name: str
    recommendation_type: str # 'Reorder', 'Reduce Safety Stock', 'Liquidate'
    current_level: float
    suggested_level: float
    rationale: str
    potential_savings: float

class InventoryAlert(BaseModel):
    alert_type: str # 'Low Stock', 'Overstock', 'Expiry Risk'
    severity: str # 'Critical', 'High', 'Medium', 'Low'
    message: str
    item_id: uuid.UUID | None = None
    batch_id: uuid.UUID | None = None

class CopilotQuery(BaseModel):
    query: str = Field(..., max_length=512)

class CopilotResponse(BaseModel):
    intent: str
    response_text: str
    action_type: str | None = None
    action_payload: dict | None = None

class InventoryInsightsDashboard(BaseModel):
    health_score: float = Field(..., ge=0, le=100)
    total_alerts: int
    optimization_opportunities: int
    forecasts: list[InventoryForecast]
    recommendations: list[OptimizationRecommendation]
    alerts: list[InventoryAlert]
