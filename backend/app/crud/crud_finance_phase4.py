from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from datetime import timezone, timezone
from decimal import Decimal

from app.models.finance_phase4 import (
    FixedAssetCategory, FixedAsset, AssetDepreciationLog,
    CostCenter, ProfitCenter, Budget, BudgetLine, Forecast
)
from app.schemas.finance_phase4 import (
    FixedAssetCategoryCreate, FixedAssetCreate,
    CostCenterCreate, ProfitCenterCreate,
    BudgetCreate, ForecastCreate
)

class CRUDFinancePhase4:
    # --- Fixed Assets ---
    async def create_asset_category(self, db: AsyncSession, obj_in: FixedAssetCategoryCreate) -> FixedAssetCategory:
        db_obj = FixedAssetCategory(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_asset_categories(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[FixedAssetCategory]:
        result = await db.execute(select(FixedAssetCategory).where(FixedAssetCategory.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_fixed_asset(self, db: AsyncSession, obj_in: FixedAssetCreate) -> FixedAsset:
        db_obj = FixedAsset(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_fixed_assets(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[FixedAsset]:
        result = await db.execute(select(FixedAsset).where(FixedAsset.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def run_depreciation(self, db: AsyncSession, tenant_id: UUID) -> dict:
        """
        Calculates and posts depreciation for all active assets for the tenant.
        Returns the number of assets depreciated and total amount.
        """
        # 1. Fetch all active assets for tenant
        assets_query = await db.execute(select(FixedAsset).where(
            FixedAsset.tenant_id == tenant_id,
            FixedAsset.status == "ACTIVE"
        ))
        assets = assets_query.scalars().all()
        
        depreciated_count = 0
        total_depreciation = Decimal("0.00")
        
        # Current date for log
        now = datetime.now(timezone.utc)
        
        for asset in assets:
            if asset.current_value <= asset.salvage_value:
                continue # Fully depreciated
                
            depreciation_amount = Decimal("0.00")
            
            # Straight Line Method (SLM)
            if asset.depreciation_method.value == "SLM":
                # Annual depreciation = (Cost - Salvage) / Useful Life
                annual_dep = (asset.acquisition_cost - asset.salvage_value) / asset.useful_life_years
                # For simplicity in this engine, we'll calculate a monthly chunk if we assume it runs monthly
                monthly_dep = annual_dep / 12
                depreciation_amount = monthly_dep
                
            # Written Down Value (WDV)
            elif asset.depreciation_method.value == "WDV":
                # Annual depreciation = Current Value * Rate
                annual_dep = asset.current_value * (asset.depreciation_rate / Decimal('100.0'))
                monthly_dep = annual_dep / 12
                depreciation_amount = monthly_dep
            
            # Ensure we don't depreciate below salvage value
            if asset.current_value - depreciation_amount < asset.salvage_value:
                depreciation_amount = asset.current_value - asset.salvage_value
                
            if depreciation_amount > 0:
                asset.current_value -= depreciation_amount
                
                # Log it
                log = AssetDepreciationLog(
                    tenant_id=tenant_id,
                    asset_id=asset.id,
                    depreciation_date=now,
                    depreciation_amount=depreciation_amount
                )
                db.add(log)
                depreciated_count += 1
                total_depreciation += depreciation_amount
                
                # Note: In a full system, here we would also call Phase 1 CRUD to generate
                # the automated Journal Voucher for Depreciation Expense vs Accumulated Depreciation
                
        await db.flush()
        return {
            "assets_depreciated": depreciated_count,
            "total_depreciation_amount": float(total_depreciation)
        }

    # --- Cost & Profit Centers ---
    async def create_cost_center(self, db: AsyncSession, obj_in: CostCenterCreate) -> CostCenter:
        db_obj = CostCenter(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_cost_centers(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[CostCenter]:
        result = await db.execute(select(CostCenter).where(CostCenter.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_profit_center(self, db: AsyncSession, obj_in: ProfitCenterCreate) -> ProfitCenter:
        db_obj = ProfitCenter(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_profit_centers(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[ProfitCenter]:
        result = await db.execute(select(ProfitCenter).where(ProfitCenter.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    # --- Budgets & Forecasts ---
    async def create_budget(self, db: AsyncSession, obj_in: BudgetCreate) -> Budget:
        lines = obj_in.lines
        budget_data = obj_in.model_dump(exclude={"lines"})
        db_budget = Budget(**budget_data)
        db.add(db_budget)
        await db.flush() # get ID
        
        for line in lines:
            db_line = BudgetLine(
                tenant_id=obj_in.tenant_id,
                budget_id=db_budget.id,
                account_id=line.account_id,
                allocated_amount=line.allocated_amount
            )
            db.add(db_line)
            
        await db.flush()
        await db.refresh(db_budget)
        return db_budget

    async def get_budgets(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Budget]:
        result = await db.execute(select(Budget).where(Budget.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_forecast(self, db: AsyncSession, obj_in: ForecastCreate) -> Forecast:
        db_obj = Forecast(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_forecasts(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Forecast]:
        result = await db.execute(select(Forecast).where(Forecast.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

finance_phase4 = CRUDFinancePhase4()
