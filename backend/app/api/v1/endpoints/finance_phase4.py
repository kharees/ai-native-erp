from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.middleware.tenant_auth import get_verified_tenant_id
from app.middleware.rbac import RequirePermission
from app.services.audit import AuditLogger

from app.crud.crud_finance_phase4 import finance_phase4
from app.schemas.finance_phase4 import (
    FixedAssetCategoryCreate, FixedAssetCategoryOut,
    FixedAssetCreate, FixedAssetOut,
    CostCenterCreate, CostCenterOut,
    ProfitCenterCreate, ProfitCenterOut,
    BudgetCreate, BudgetOut,
    ForecastCreate, ForecastOut
)

log = structlog.get_logger(__name__)
router = APIRouter()

# --- Fixed Assets ---
@router.post("/assets/categories", response_model=FixedAssetCategoryOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "FixedAsset", "Create"))])
async def create_asset_category(request: Request, payload: FixedAssetCategoryCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase4.create_asset_category(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_ASSET_CATEGORY", resource_id=str(result.id))
    return result

@router.get("/assets/categories", response_model=List[FixedAssetCategoryOut], dependencies=[Depends(RequirePermission("Finance", "FixedAsset", "Read"))])
async def list_asset_categories(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_phase4.get_asset_categories(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/assets", response_model=FixedAssetOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "FixedAsset", "Create"))])
async def create_fixed_asset(request: Request, payload: FixedAssetCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase4.create_fixed_asset(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_FIXED_ASSET", resource_id=str(result.id))
    return result

@router.get("/assets", response_model=List[FixedAssetOut], dependencies=[Depends(RequirePermission("Finance", "FixedAsset", "Read"))])
async def list_fixed_assets(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_phase4.get_fixed_assets(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/assets/run-depreciation", dependencies=[Depends(RequirePermission("Finance", "FixedAsset", "Update"))])
async def trigger_run_depreciation(request: Request, db: AsyncSession = Depends(get_db)):
    """Runs depreciation computation for the current month across all active assets"""
    tenant_id = await get_verified_tenant_id(request)
    result = await finance_phase4.run_depreciation(db, tenant_id)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="RUN_DEPRECIATION")
    return result

# --- Cost Centers ---
@router.post("/cost-centers", response_model=CostCenterOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "CostCenter", "Create"))])
async def create_cost_center(request: Request, payload: CostCenterCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase4.create_cost_center(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_COST_CENTER", resource_id=str(result.id))
    return result

@router.get("/cost-centers", response_model=List[CostCenterOut], dependencies=[Depends(RequirePermission("Finance", "CostCenter", "Read"))])
async def list_cost_centers(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_phase4.get_cost_centers(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/profit-centers", response_model=ProfitCenterOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "ProfitCenter", "Create"))])
async def create_profit_center(request: Request, payload: ProfitCenterCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase4.create_profit_center(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_PROFIT_CENTER", resource_id=str(result.id))
    return result

@router.get("/profit-centers", response_model=List[ProfitCenterOut], dependencies=[Depends(RequirePermission("Finance", "ProfitCenter", "Read"))])
async def list_profit_centers(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_phase4.get_profit_centers(db, tenant_id=tenant_id, skip=skip, limit=limit)

# --- Budgets & Forecasts ---
@router.post("/budgets", response_model=BudgetOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "Budget", "Create"))])
async def create_budget(request: Request, payload: BudgetCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase4.create_budget(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_BUDGET", resource_id=str(result.id))
    return result

@router.get("/budgets", response_model=List[BudgetOut], dependencies=[Depends(RequirePermission("Finance", "Budget", "Read"))])
async def list_budgets(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_phase4.get_budgets(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/forecasts", response_model=ForecastOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "Forecast", "Create"))])
async def create_forecast(request: Request, payload: ForecastCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase4.create_forecast(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_FORECAST", resource_id=str(result.id))
    return result

@router.get("/forecasts", response_model=List[ForecastOut], dependencies=[Depends(RequirePermission("Finance", "Forecast", "Read"))])
async def list_forecasts(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_phase4.get_forecasts(db, tenant_id=tenant_id, skip=skip, limit=limit)
