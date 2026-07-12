"""
app/services/agent_adapters/finance_tools.py
==============================================
Sprint 5 (#2): agent-safe adapters over app/crud/crud_finance_core.py.

Every function here is decorated with @agent_tool (app/services/
agent_adapters/base.py), which structurally forbids an AsyncSession/
AsyncConnection parameter — enforced at import time, not just by
convention. Each function opens and closes its own session internally via
db_session() and returns a plain Pydantic schema (already detached from
the session by the time it's returned), never an ORM object.

create_and_post_journal_voucher is the flagship example of why this layer
exists as more than a signature-hiding wrapper: docs/ai-foundation.md
flagged that an agent chaining "create voucher" then "approve voucher" as
two separate tool calls has no atomicity between them — a crash between
the two leaves a permanently-unposted draft with no way to tell whether
that was intentional. Exposing the two-step operation as one tool call
that opens exactly one session/transaction removes that failure mode
entirely, the same way Sprint 5 #1 fixed it for regular API endpoints.
"""

from __future__ import annotations

import uuid
from typing import Optional

from app.core.database import db_session
from app.crud.crud_finance_core import finance_core
from app.schemas.finance_core import (
    AccountCreate,
    AccountOut,
    JournalEntryLineCreate,
    JournalVoucherCreate,
    JournalVoucherOut,
)
from app.services.agent_adapters.base import agent_tool


@agent_tool
async def get_account(tenant_id: uuid.UUID, account_id: uuid.UUID) -> Optional[AccountOut]:
    """Fetch one Chart-of-Accounts account by id, scoped to tenant_id."""
    async with db_session() as db:
        obj = await finance_core.get_account(db, account_id, tenant_id)
        return AccountOut.model_validate(obj) if obj else None


@agent_tool
async def list_accounts(tenant_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[AccountOut]:
    """List Chart-of-Accounts accounts for a tenant, paginated."""
    async with db_session() as db:
        objs = await finance_core.get_accounts(db, tenant_id, skip=skip, limit=limit)
        return [AccountOut.model_validate(o) for o in objs]


@agent_tool
async def create_account(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    account_code: str,
    name: str,
    account_type: str,
    normal_balance: str,
) -> AccountOut:
    """Create a new Chart-of-Accounts account."""
    async with db_session() as db:
        obj_in = AccountCreate(
            tenant_id=tenant_id,
            group_id=group_id,
            account_code=account_code,
            name=name,
            account_type=account_type,
            normal_balance=normal_balance,
        )
        obj = await finance_core.create_account(db, obj_in)
        return AccountOut.model_validate(obj)


@agent_tool
async def create_and_post_journal_voucher(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    voucher_number: str,
    entry_date,
    lines: list[dict],
    reference: Optional[str] = None,
    description: Optional[str] = None,
) -> JournalVoucherOut:
    """
    Create a journal voucher and immediately post it, as one atomic
    operation. `lines` is a list of {account_id, debit, credit,
    description?} dicts; debits must equal credits or the whole call fails
    with nothing persisted.
    """
    async with db_session() as db:
        obj_in = JournalVoucherCreate(
            tenant_id=tenant_id,
            voucher_number=voucher_number,
            entry_date=entry_date,
            reference=reference,
            description=description,
            lines=[JournalEntryLineCreate(**line) for line in lines],
        )
        voucher = await finance_core.create_journal_voucher(db, obj_in, user_id)
        posted = await finance_core.approve_journal_voucher(db, voucher.id, tenant_id, user_id)
        return JournalVoucherOut.model_validate(posted)
