from typing import Optional
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.middleware.rbac import RequirePermission
from app.services.audit import AuditLogger
from app.services.finance_reports import finance_reports_service
from app.schemas.finance_reports import (
    TrialBalanceReport,
    ProfitAndLossReport,
    BalanceSheetReport,
    CashFlowReport
)

log = structlog.get_logger(__name__)
router = APIRouter()

def get_tenant_id(request: Request) -> UUID:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant context")
    return tenant_id

@router.get("/trial-balance", response_model=TrialBalanceReport, dependencies=[Depends(RequirePermission("Finance", "Reports", "Read"))])
async def get_trial_balance(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE_REPORTING", action_type="GENERATE_TRIAL_BALANCE")
    return await finance_reports_service.generate_trial_balance(db, tenant_id, start_date, end_date)

@router.get("/profit-and-loss", response_model=ProfitAndLossReport, dependencies=[Depends(RequirePermission("Finance", "Reports", "Read"))])
async def get_profit_and_loss(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE_REPORTING", action_type="GENERATE_PROFIT_AND_LOSS")
    return await finance_reports_service.generate_profit_and_loss(db, tenant_id, start_date, end_date)

@router.get("/balance-sheet", response_model=BalanceSheetReport, dependencies=[Depends(RequirePermission("Finance", "Reports", "Read"))])
async def get_balance_sheet(
    request: Request,
    as_of_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    if not as_of_date:
        as_of_date = date.today()
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE_REPORTING", action_type="GENERATE_BALANCE_SHEET")
    return await finance_reports_service.generate_balance_sheet(db, tenant_id, as_of_date)

@router.get("/cash-flow", response_model=CashFlowReport, dependencies=[Depends(RequirePermission("Finance", "Reports", "Read"))])
async def get_cash_flow(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE_REPORTING", action_type="GENERATE_CASH_FLOW")
    return await finance_reports_service.generate_cash_flow(db, tenant_id, start_date, end_date)

@router.get("/dashboard-summary", dependencies=[Depends(RequirePermission("Finance", "Reports", "Read"))])
async def get_dashboard_summary(
    request: Request,
    as_of_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    if not as_of_date:
        as_of_date = date.today()
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE_REPORTING", action_type="GENERATE_DASHBOARD_SUMMARY")
    return await finance_reports_service.generate_dashboard_summary(db, tenant_id, as_of_date)
