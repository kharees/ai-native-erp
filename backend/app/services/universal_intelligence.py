import uuid
import random
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.universal_intelligence import (
    InventoryForecast,
    OptimizationRecommendation,
    InventoryAlert,
    CopilotResponse,
    InventoryInsightsDashboard
)

class UniversalInventoryAnalyzer:
    @staticmethod
    async def get_dashboard(db: AsyncSession, tenant_id: uuid.UUID) -> InventoryInsightsDashboard:
        # Mock AI generation based on heuristics
        return InventoryInsightsDashboard(
            health_score=87.5,
            total_alerts=3,
            optimization_opportunities=2,
            forecasts=[
                InventoryForecast(
                    item_id=uuid.uuid4(),
                    item_name="Premium Widget A",
                    current_stock=150.0,
                    projected_demand_30d=200.0,
                    confidence_score=0.92,
                    seasonality_trend="Increasing"
                )
            ],
            recommendations=[
                OptimizationRecommendation(
                    item_id=uuid.uuid4(),
                    item_name="Standard Gadget B",
                    recommendation_type="Liquidate",
                    current_level=5000.0,
                    suggested_level=1000.0,
                    rationale="Overstocked based on trailing 90-day velocity. 180+ days of supply.",
                    potential_savings=12500.0
                )
            ],
            alerts=[
                InventoryAlert(
                    alert_type="Expiry Risk",
                    severity="High",
                    message="Batch B-990 expires in 14 days.",
                    item_id=uuid.uuid4()
                )
            ]
        )

    @staticmethod
    async def process_copilot_query(db: AsyncSession, tenant_id: uuid.UUID, query: str) -> CopilotResponse:
        # Simple heuristic parser for the mock AI
        query_lower = query.lower()
        
        if "low stock" in query_lower:
            return CopilotResponse(
                intent="FIND_LOW_STOCK",
                response_text="I found 5 items currently below their minimum safety stock levels.",
                action_type="NAVIGATE_REPORTS",
                action_payload={"filter": "low_stock"}
            )
        elif "dead" in query_lower or "slow" in query_lower:
            return CopilotResponse(
                intent="FIND_DEAD_STOCK",
                response_text="There is approximately $45,000 tied up in stock that hasn't moved in 180 days.",
                action_type="NAVIGATE_REPORTS",
                action_payload={"filter": "dead_stock"}
            )
        elif "expire" in query_lower or "expiry" in query_lower:
            return CopilotResponse(
                intent="FIND_EXPIRY",
                response_text="You have 3 batches expiring within the next 30 days.",
                action_type="NAVIGATE_TRACKING",
                action_payload={"filter": "expiry_30_days"}
            )
        else:
            return CopilotResponse(
                intent="GENERAL_INVENTORY_ASSIST",
                response_text="I can help you forecast demand, optimize safety stock, or identify risky inventory. What would you like to explore?",
                action_type=None,
                action_payload=None
            )
