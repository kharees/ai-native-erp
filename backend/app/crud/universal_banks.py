import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_banks import UniversalBankAccount, UniversalBankVoucher
from app.schemas.universal_banks import (
    UniversalBankAccountCreate, UniversalBankAccountUpdate,
    UniversalBankVoucherCreate, UniversalBankVoucherUpdate
)

async def create_bank_account(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalBankAccountCreate) -> UniversalBankAccount:
    obj = UniversalBankAccount(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_bank_accounts(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalBankAccount).where(UniversalBankAccount.tenant_id == tenant_id).order_by(UniversalBankAccount.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalBankAccount.id)).where(UniversalBankAccount.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_bank_voucher(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalBankVoucherCreate) -> UniversalBankVoucher:
    # Ownership validated before any write: db.get() is a primary-key-only
    # lookup with no tenant filter — a bank_account_id belonging to another
    # tenant would previously be found and have its real current_balance
    # mutated by this tenant's voucher (Sprint 5 #3 verification finding,
    # CRITICAL). A tenant-scoped select() closes that.
    bank_stmt = select(UniversalBankAccount).where(
        UniversalBankAccount.id == payload.bank_account_id,
        UniversalBankAccount.tenant_id == tenant_id,
    )
    bank = (await db.execute(bank_stmt)).scalar_one_or_none()

    obj = UniversalBankVoucher(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)

    # Update bank balance
    if bank:
        if payload.voucher_type == "RECEIPT":
            bank.current_balance += payload.amount
        elif payload.voucher_type == "PAYMENT":
            bank.current_balance -= payload.amount
            
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_bank_vouchers(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalBankVoucher).where(UniversalBankVoucher.tenant_id == tenant_id).order_by(UniversalBankVoucher.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalBankVoucher.id)).where(UniversalBankVoucher.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
