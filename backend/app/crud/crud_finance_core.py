from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from decimal import Decimal

from app.models.finance_core import AccountGroup, Account, JournalVoucher, JournalEntryLine, JournalStatus
from app.schemas.finance_core import (
    AccountGroupCreate, AccountGroupUpdate,
    AccountCreate, AccountUpdate,
    JournalVoucherCreate, JournalVoucherUpdate
)

class CRUDFinanceCore:
    # --- Account Group ---
    async def create_account_group(self, db: AsyncSession, obj_in: AccountGroupCreate) -> AccountGroup:
        db_obj = AccountGroup(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_account_group(self, db: AsyncSession, id: UUID, tenant_id: UUID) -> Optional[AccountGroup]:
        result = await db.execute(select(AccountGroup).where(AccountGroup.id == id, AccountGroup.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def get_account_groups(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[AccountGroup]:
        result = await db.execute(select(AccountGroup).where(AccountGroup.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update_account_group(self, db: AsyncSession, db_obj: AccountGroup, obj_in: AccountGroupUpdate) -> AccountGroup:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    # --- Account ---
    async def create_account(self, db: AsyncSession, obj_in: AccountCreate) -> Account:
        db_obj = Account(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_account(self, db: AsyncSession, id: UUID, tenant_id: UUID) -> Optional[Account]:
        result = await db.execute(select(Account).where(Account.id == id, Account.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def get_accounts(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Account]:
        result = await db.execute(select(Account).where(Account.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update_account(self, db: AsyncSession, db_obj: Account, obj_in: AccountUpdate) -> Account:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    # --- Journal Voucher ---
    async def create_journal_voucher(self, db: AsyncSession, obj_in: JournalVoucherCreate, user_id: UUID) -> JournalVoucher:
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        
        for line in obj_in.lines:
            total_debit += line.debit
            total_credit += line.credit
            
        if total_debit != total_credit:
            raise HTTPException(status_code=400, detail="Journal entry must balance (Debits must equal Credits).")
            
        voucher_data = obj_in.model_dump(exclude={'lines'})
        voucher_data['total_debit'] = total_debit
        voucher_data['total_credit'] = total_credit
        voucher_data['created_by'] = user_id
        
        db_voucher = JournalVoucher(**voucher_data)
        db.add(db_voucher)
        await db.flush()
        
        for line_in in obj_in.lines:
            line_data = line_in.model_dump()
            line_data['tenant_id'] = db_voucher.tenant_id
            line_data['voucher_id'] = db_voucher.id
            db_line = JournalEntryLine(**line_data)
            db.add(db_line)
            
        await db.commit()
        await db.refresh(db_voucher)
        
        # Load lines for response
        await db.refresh(db_voucher, ['lines'])
        return db_voucher

    async def get_journal_voucher(self, db: AsyncSession, id: UUID, tenant_id: UUID) -> Optional[JournalVoucher]:
        result = await db.execute(select(JournalVoucher).where(JournalVoucher.id == id, JournalVoucher.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def get_journal_vouchers(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[JournalVoucher]:
        result = await db.execute(select(JournalVoucher).where(JournalVoucher.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().unique().all())
        
    async def approve_journal_voucher(self, db: AsyncSession, id: UUID, tenant_id: UUID, user_id: UUID) -> JournalVoucher:
        db_voucher = await self.get_journal_voucher(db, id, tenant_id)
        if not db_voucher:
            raise HTTPException(status_code=404, detail="Journal voucher not found")
            
        if db_voucher.status not in [JournalStatus.PENDING_APPROVAL, JournalStatus.DRAFT]:
            raise HTTPException(status_code=400, detail="Only draft or pending vouchers can be approved")
            
        db_voucher.status = JournalStatus.POSTED
        db_voucher.approved_by = user_id
        db.add(db_voucher)
        await db.commit()
        await db.refresh(db_voucher)
        await db.refresh(db_voucher, ['lines'])
        return db_voucher

finance_core = CRUDFinanceCore()
