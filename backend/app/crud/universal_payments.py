import uuid
from decimal import Decimal
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_payments import (
    UniversalPaymentReceipt, UniversalPaymentAllocation,
    UniversalRefund, UniversalCustomerWallet
)
from app.schemas.universal_payments import (
    UniversalPaymentReceiptCreate, UniversalPaymentAllocationCreate,
    UniversalRefundCreate
)

async def create_payment_receipt(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalPaymentReceiptCreate) -> UniversalPaymentReceipt:
    obj = UniversalPaymentReceipt(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    
    # Update customer wallet if unallocated
    if obj.unallocated_amount > 0:
        wallet = (await db.execute(select(UniversalCustomerWallet).where(UniversalCustomerWallet.customer_id == obj.customer_id))).scalar_one_or_none()
        if not wallet:
            wallet = UniversalCustomerWallet(tenant_id=tenant_id, customer_id=obj.customer_id, balance=0.0)
            db.add(wallet)
            await db.flush()
        # wallet.balance is a Numeric column (Decimal) once fetched fresh
        # from the DB (as opposed to a just-constructed Python object where
        # it's still the raw float passed to the constructor above); mixing
        # Decimal += float raises TypeError. Only ever surfaced for a
        # customer's second+ receipt, since the first always hits the
        # freshly-constructed-object path instead.
        wallet.balance += Decimal(str(obj.unallocated_amount))

    await db.commit()
    await db.refresh(obj)
    return obj

async def list_payment_receipts(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalPaymentReceipt).where(UniversalPaymentReceipt.tenant_id == tenant_id).order_by(UniversalPaymentReceipt.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalPaymentReceipt.id)).where(UniversalPaymentReceipt.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_payment_allocation(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalPaymentAllocationCreate) -> UniversalPaymentAllocation:
    obj = UniversalPaymentAllocation(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    
    receipt = await db.get(UniversalPaymentReceipt, payload.receipt_id)
    if receipt:
        receipt.unallocated_amount -= payload.allocated_amount
        
        wallet = (await db.execute(select(UniversalCustomerWallet).where(UniversalCustomerWallet.customer_id == receipt.customer_id))).scalar_one_or_none()
        if wallet:
            wallet.balance -= payload.allocated_amount

    await db.commit()
    await db.refresh(obj)
    return obj

async def create_refund(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalRefundCreate) -> UniversalRefund:
    obj = UniversalRefund(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_refunds(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalRefund).where(UniversalRefund.tenant_id == tenant_id).order_by(UniversalRefund.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalRefund.id)).where(UniversalRefund.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
