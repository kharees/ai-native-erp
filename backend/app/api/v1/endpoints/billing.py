"""
app/api/v1/endpoints/billing.py
===============================
Asynchronous endpoint router layer for the Omnichannel Billing & Invoice Engine.
"""

import uuid
from datetime import datetime
from datetime import timezone, timezone
from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import structlog

from app.core.database import get_db
from app.models.billing import TenantBillingInvoice
from app.schemas.billing import BillingInvoiceCreate, BillingInvoiceResponse
from app.middleware.rbac import RequirePermission


log = structlog.get_logger(__name__)
router = APIRouter()


def generate_invoice_code() -> str:
    """Generate a unique tracking code for the invoice."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short_uuid = str(uuid.uuid4())[:8].upper()
    return f"INV-{timestamp}-{short_uuid}"


@router.post(
    "/",
    response_model=BillingInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new billing invoice",
    dependencies=[Depends(RequirePermission("Billing", "Invoices", "Create"))],
)
async def create_invoice(
    request: Request,
    payload: BillingInvoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> TenantBillingInvoice:
    """
    Securely ingest the payload schema, extract tenant context from the
    global Auth middleware layer, generate a unique invoice code token string,
    and push data down to backend repository engines.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant context. Ensure request passes through TenantAuthMiddleware.",
        )
    
    # 1. Enforce business rules securely at the edge
    if payload.total_amount != (payload.subtotal + payload.tax_amount):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invoice integrity failure: total_amount must equal subtotal + tax_amount",
        )

    # 2. Build model instance
    invoice_number = generate_invoice_code()
    
    # Dump payload safely to dict, translating enums
    payload_dict = payload.model_dump(exclude_unset=True)
    # Serialize nested items snapshot cleanly
    items_snapshot_raw = [item.model_dump() for item in payload.items_snapshot]
    payload_dict["items_snapshot"] = items_snapshot_raw

    db_invoice = TenantBillingInvoice(
        tenant_id=tenant_id,
        invoice_number=invoice_number,
        **payload_dict,
    )
    
    # 3. Commit to database
    db.add(db_invoice)
    try:
        await db.flush()
        await db.refresh(db_invoice)
        log.info("invoice_created", invoice_number=db_invoice.invoice_number, tenant_id=str(tenant_id))
        return db_invoice
    except IntegrityError as e:
        await db.rollback()
        log.error("invoice_creation_failed", error=str(e), tenant_id=str(tenant_id))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict occurred during invoice creation. Possible duplicate reference.",
        )


@router.get(
    "/",
    response_model=List[BillingInvoiceResponse],
    summary="Retrieve invoice history",
    dependencies=[Depends(RequirePermission("Billing", "Invoices", "Read"))],
)
async def get_invoice_history(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> Sequence[TenantBillingInvoice]:
    """
    GET route using the isolated context parameter 'X-Tenant-ID' row-level 
    boundary rules to safely filter array histories.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant context. Ensure request passes through TenantAuthMiddleware.",
        )

    stmt = (
        select(TenantBillingInvoice)
        .where(TenantBillingInvoice.tenant_id == tenant_id)
        .where(TenantBillingInvoice.is_active == True)
        .order_by(TenantBillingInvoice.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    invoices = result.scalars().all()
    
    log.info("invoice_history_retrieved", count=len(invoices), tenant_id=str(tenant_id))
    return invoices
