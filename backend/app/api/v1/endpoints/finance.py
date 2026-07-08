"""
app/api/v1/endpoints/finance.py
===============================
Asynchronous endpoint router layer for the AI Copilot Ledger & Finance Engine.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import structlog

from app.core.database import get_db
from app.models.finance import TenantFinanceLedger, TransactionType
from app.schemas.finance import (
    FinanceLedgerCreate,
    FinanceLedgerResponse,
    FinanceSummaryResponse,
)


log = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=FinanceLedgerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new ledger transaction",
)
async def record_transaction(
    request: Request,
    payload: FinanceLedgerCreate,
    db: AsyncSession = Depends(get_db),
) -> TenantFinanceLedger:
    """
    Extracts the active user's 'X-Tenant-ID' context, processes AI insight 
    metadata validation models, and securely commits the data payload map.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant context. Ensure request passes through TenantAuthMiddleware.",
        )

    # Convert payload securely
    payload_dict = payload.model_dump(exclude_unset=True)

    # Initialize the ORM model
    db_ledger = TenantFinanceLedger(
        tenant_id=tenant_id,
        **payload_dict,
    )
    
    db.add(db_ledger)
    try:
        await db.commit()
        await db.refresh(db_ledger)
        log.info(
            "finance_transaction_recorded", 
            transaction_type=db_ledger.transaction_type, 
            amount=str(db_ledger.amount),
            tenant_id=str(tenant_id)
        )
        return db_ledger
    except IntegrityError as e:
        await db.rollback()
        log.error("finance_transaction_failed", error=str(e), tenant_id=str(tenant_id))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database integrity failure while committing financial record.",
        )


@router.get(
    "/summary",
    response_model=FinanceSummaryResponse,
    summary="Retrieve multi-tenant financial summary",
)
async def get_finance_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FinanceSummaryResponse:
    """
    Aggregates multi-tenant income vs expense accounting parameters cleanly
    using isolated X-Tenant-ID SQL sum grouped logic.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant context. Ensure request passes through TenantAuthMiddleware.",
        )

    # Using native SQL aggregation for performance optimization on large datasets
    stmt = (
        select(
            TenantFinanceLedger.transaction_type,
            func.sum(TenantFinanceLedger.amount).label("total")
        )
        .where(TenantFinanceLedger.tenant_id == tenant_id)
        .where(TenantFinanceLedger.is_active == True)
        .group_by(TenantFinanceLedger.transaction_type)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")
    
    for row in rows:
        t_type = row.transaction_type
        # Coerce SQL sum result safely to Decimal
        t_sum = Decimal(str(row.total)) if row.total else Decimal("0.00")
        
        if t_type == TransactionType.INCOME:
            total_income = t_sum
        elif t_type == TransactionType.EXPENSE:
            total_expense = t_sum

    net_balance = total_income - total_expense

    log.info("finance_summary_retrieved", tenant_id=str(tenant_id), net_balance=str(net_balance))
    
    return FinanceSummaryResponse(
        tenant_id=tenant_id,
        total_income=total_income,
        total_expense=total_expense,
        net_balance=net_balance,
        currency="INR"
    )
