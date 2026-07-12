from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal

from app.models.finance_core import AccountGroup, Account, JournalVoucher, JournalEntryLine, JournalStatus
from app.schemas.finance_core import (
    AccountGroupCreate, AccountGroupUpdate,
    AccountCreate, AccountUpdate,
    JournalVoucherCreate, JournalVoucherUpdate
)
from app.services.outbox import enqueue_event


class FinanceCoreError(Exception):
    """
    Domain error for finance-core CRUD operations.

    Deliberately not an HTTPException: this module is the persistence layer
    and must stay usable from contexts that have no FastAPI request in scope
    (background jobs, an AI tool-calling copilot, tests). The endpoint layer
    (see app/api/v1/endpoints/finance_core.py) and the global exception
    handler in main.py translate this into the appropriate HTTP response.
    """
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class CRUDFinanceCore:
    """
    Unit-of-work note
    ------------------
    None of the methods below call ``db.commit()``. They ``flush()`` instead,
    which sends pending SQL to the open transaction (assigning server-side
    defaults/IDs and making the rows visible to subsequent queries on the
    same connection) without ending the transaction. The caller — the route
    handler — owns the commit boundary and calls ``db.commit()`` once, after
    everything it needs to do for that request has succeeded. If anything
    raises before that commit (including a `FinanceCoreError` raised by this
    class), the `get_db()` dependency's `db_session()` context manager rolls
    the whole transaction back, so a validation failure never leaves a
    half-written voucher or account behind.
    """

    # --- Account Group ---
    async def create_account_group(self, db: AsyncSession, obj_in: AccountGroupCreate) -> AccountGroup:
        db_obj = AccountGroup(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
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
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    # --- Account ---
    async def create_account(self, db: AsyncSession, obj_in: AccountCreate) -> Account:
        db_obj = Account(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
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
        expected_version = update_data.pop("expected_version", None)
        if expected_version is not None and expected_version != db_obj.version:
            raise FinanceCoreError(
                f"Account was modified by someone else (expected version {expected_version}, "
                f"current version is {db_obj.version}). Reload and retry.",
                409,
            )
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        db_obj.version += 1
        db.add(db_obj)
        await db.flush()
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
            raise FinanceCoreError("Journal entry must balance (Debits must equal Credits).", 400)

        # Every line's account must exist and belong to this tenant — nothing
        # previously stopped a line from referencing an account_id from a
        # different tenant entirely.
        account_ids = {line.account_id for line in obj_in.lines}
        if account_ids:
            result = await db.execute(
                select(Account.id).where(Account.id.in_(account_ids), Account.tenant_id == obj_in.tenant_id)
            )
            found_ids = {row[0] for row in result.all()}
            missing = account_ids - found_ids
            if missing:
                missing_str = ", ".join(str(m) for m in missing)
                raise FinanceCoreError(
                    f"One or more accounts do not exist for this tenant: {missing_str}", 400
                )

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

        await db.flush()
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
        """
        Posts a journal voucher. This is the only state transition allowed
        into JournalStatus.POSTED, and it is a one-way door: a voucher that
        is already POSTED or REVERSED is rejected here, and there is no
        update/delete route for journal vouchers anywhere in the API, so a
        posted voucher's lines and totals can never be mutated afterward —
        correcting a posted entry requires a new, separate reversing
        voucher, not an edit of the original.
        """
        db_voucher = await self.get_journal_voucher(db, id, tenant_id)
        if not db_voucher:
            raise FinanceCoreError("Journal voucher not found", 404)

        if db_voucher.status not in [JournalStatus.PENDING_APPROVAL, JournalStatus.DRAFT]:
            raise FinanceCoreError(
                "Only draft or pending vouchers can be approved. Posted vouchers are immutable.", 400
            )

        db_voucher.status = JournalStatus.POSTED
        db_voucher.approved_by = user_id
        db.add(db_voucher)

        # Transactional outbox (audit #37): written in the same flush/commit
        # as the posting above, via the same session — either both persist
        # or neither does. First real domain event emitted anywhere in the
        # backend; a downstream consumer (webhook, AI trigger, etc.) can
        # subscribe to "journal_voucher.posted" instead of polling once a
        # relay/dispatcher exists (not built here — see
        # docs/production-hardening.md).
        await enqueue_event(db, tenant_id, "journal_voucher.posted", {
            "voucher_id": str(db_voucher.id),
            "voucher_number": db_voucher.voucher_number,
            "total_debit": str(db_voucher.total_debit),
            "total_credit": str(db_voucher.total_credit),
            "approved_by": str(user_id),
        })

        await db.flush()
        await db.refresh(db_voucher)
        await db.refresh(db_voucher, ['lines'])
        return db_voucher

finance_core = CRUDFinanceCore()
