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
        wallet = (await db.execute(select(UniversalCustomerWallet).where(
            UniversalCustomerWallet.customer_id == obj.customer_id,
            UniversalCustomerWallet.tenant_id == tenant_id,
        ))).scalar_one_or_none()
        if not wallet:
            wallet = UniversalCustomerWallet(tenant_id=tenant_id, customer_id=obj.customer_id, balance=0.0)
            db.add(wallet)
            await db.flush()
        # wallet.balance is a Numeric column (Decimal) once fetched fresh
        # from the DB, but still a raw float on a just-constructed object
        # (the 0.0 passed to the constructor above) until it's flushed and
        # refreshed. Wrapping the current value in Decimal(str(...)) before
        # adding makes this correct either way, instead of relying on
        # wallet.balance already being a Decimal (previously true only for
        # a customer's second+ receipt, since the first always hit the
        # freshly-constructed-object path and raised TypeError on +=).
        wallet.balance = Decimal(str(wallet.balance)) + Decimal(str(obj.unallocated_amount))

    await db.flush()
    await db.refresh(obj)
    return obj

async def list_payment_receipts(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalPaymentReceipt).where(UniversalPaymentReceipt.tenant_id == tenant_id).order_by(UniversalPaymentReceipt.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalPaymentReceipt.id)).where(UniversalPaymentReceipt.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_payment_allocation(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalPaymentAllocationCreate) -> UniversalPaymentAllocation:
    obj = UniversalPaymentAllocation(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    
    # db.get() looks up by primary key only — no tenant filter — so a
    # receipt_id belonging to a different tenant used to be found and
    # mutated here anyway (its unallocated_amount decremented, and that
    # tenant's wallet balance drained, from an allocation the other tenant
    # never made). Scoping this to tenant_id closes that.
    receipt_stmt = select(UniversalPaymentReceipt).where(
        UniversalPaymentReceipt.id == payload.receipt_id,
        UniversalPaymentReceipt.tenant_id == tenant_id,
    )
    receipt = (await db.execute(receipt_stmt)).scalar_one_or_none()
    if receipt:
        # receipt.unallocated_amount is a Numeric column (Decimal), always
        # DB-fetched here; payload.allocated_amount is a plain Pydantic
        # float. Decimal -= float raises TypeError unconditionally.
        # Casting both sides through Decimal(str(...)) is correct
        # regardless of either operand's current type — same defensive
        # pattern as create_payment_receipt above.
        receipt.unallocated_amount = Decimal(str(receipt.unallocated_amount)) - Decimal(str(payload.allocated_amount))

        wallet = (await db.execute(select(UniversalCustomerWallet).where(
            UniversalCustomerWallet.customer_id == receipt.customer_id,
            UniversalCustomerWallet.tenant_id == tenant_id,
        ))).scalar_one_or_none()
        if wallet:
            wallet.balance = Decimal(str(wallet.balance)) - Decimal(str(payload.allocated_amount))

    await db.flush()
    await db.refresh(obj)
    return obj

async def create_refund(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalRefundCreate) -> UniversalRefund:
    obj = UniversalRefund(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_refunds(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalRefund).where(UniversalRefund.tenant_id == tenant_id).order_by(UniversalRefund.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalRefund.id)).where(UniversalRefund.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
