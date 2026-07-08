from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.universal_intelligence import UniversalInventoryAnalyzer
from app.schemas import universal_intelligence as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.get("/dashboard", response_model=schemas.InventoryInsightsDashboard, dependencies=[Depends(RequirePermission("UniversalInventory", "Intelligence", "Read"))])
async def get_ai_dashboard(tenant_id: TenantIDDep, db: DBDep):
    """Retrieve full AI Insights, Forecasts, and Recommendations."""
    return await UniversalInventoryAnalyzer.get_dashboard(db, tenant_id)

@router.post("/copilot/ask", response_model=schemas.CopilotResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Intelligence", "Read"))])
async def ask_copilot(request: schemas.CopilotQuery, tenant_id: TenantIDDep, db: DBDep):
    """Process Natural Language queries for Inventory insights."""
    return await UniversalInventoryAnalyzer.process_copilot_query(db, tenant_id, request.query)
