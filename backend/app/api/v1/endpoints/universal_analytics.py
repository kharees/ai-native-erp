import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_analytics as crud
from app.schemas import universal_analytics as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.get("/sales/trends", response_model=schemas.SalesSummaryResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Analytics", "Read"))])
async def get_sales_trends(tenant_id: TenantIDDep, db: DBDep, period: str = Query("monthly", description="daily, weekly, monthly, yearly")):
    return await crud.get_sales_summary(db, tenant_id, period)

@router.get("/sales/leaderboards", response_model=schemas.AnalyticsLeaderboardResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Analytics", "Read"))])
async def get_leaderboards(tenant_id: TenantIDDep, db: DBDep):
    return await crud.get_leaderboards(db, tenant_id)

@router.get("/financial/summary", response_model=schemas.FinancialSummaryResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Analytics", "Read"))])
async def get_financial_summary(tenant_id: TenantIDDep, db: DBDep):
    return await crud.get_financial_summary(db, tenant_id)
