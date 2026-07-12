"""
tests/test_agent_adapters.py
==============================
Sprint 5 (#2, audit #6): verifies the @agent_tool guard actually rejects
AsyncSession-shaped signatures, and that the adapters in
app/services/agent_adapters/ work end-to-end against the real database
(via db_session(), like tests/test_unit_of_work.py — these bypass the
app/dependency-override plumbing on purpose, so they exercise the real
commit boundary an agent call would actually run through).
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_session
from app.models.auth import UserAccount
from app.models.finance_core import AccountGroup
from app.models.tenants import Tenant
from app.models.users import UserProfile
from app.services.agent_adapters import (
    AgentToolSignatureError,
    agent_tool,
    create_account,
    create_and_post_journal_voucher,
    create_item,
    execute_stock_movement,
    get_account,
    get_item,
)


def test_agent_tool_rejects_asyncsession_parameter():
    with pytest.raises(AgentToolSignatureError):
        @agent_tool
        async def bad_tool(db: AsyncSession, tenant_id: uuid.UUID):
            ...


def test_agent_tool_rejects_unannotated_session_named_param():
    with pytest.raises(AgentToolSignatureError):
        @agent_tool
        async def bad_tool(session, tenant_id: uuid.UUID):
            ...


def test_agent_tool_accepts_clean_signature():
    @agent_tool
    async def good_tool(tenant_id: uuid.UUID, name: str) -> str:
        return name

    assert good_tool.__agent_tool__ is True


async def _make_tenant_and_group():
    async with db_session() as db:
        tenant = Tenant(name="Agent Tool Test", slug=f"agent-tool-{uuid.uuid4().hex[:10]}", plan="enterprise")
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)

        group = AccountGroup(tenant_id=tenant.id, code="AT-1000", name="Agent Test Group", category="asset")
        db.add(group)
        await db.flush()
        await db.refresh(group)
        return tenant.id, group.id


async def _make_user_account(tenant_id: uuid.UUID) -> uuid.UUID:
    # finance_journal_vouchers.created_by FKs to user_accounts.id while
    # .approved_by FKs to user_profiles.id — two different tables for what
    # the adapter treats as a single "acting user" id. Pre-existing model
    # design, not something Sprint 5 #2 changes; the test satisfies both FKs
    # by giving the profile the same id as its account.
    async with db_session() as db:
        user = UserAccount(
            email=f"agent-tool-{uuid.uuid4().hex[:10]}@example.com",
            hashed_password="not-a-real-hash",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        profile = UserProfile(id=user.id, user_id=user.id, tenant_id=tenant_id, first_name="Agent Tool Test")
        db.add(profile)
        await db.flush()
        return user.id


async def _delete_user_account(user_id: uuid.UUID) -> None:
    from sqlalchemy import delete
    async with db_session() as db:
        await db.execute(delete(UserProfile).where(UserProfile.id == user_id))
        await db.execute(delete(UserAccount).where(UserAccount.id == user_id))


async def _cleanup(tenant_id: uuid.UUID):
    from sqlalchemy import delete
    from app.models.finance_core import Account, AccountGroup as AG, JournalEntryLine, JournalVoucher
    from app.models.outbox import OutboxEvent
    from app.models.universal_inventory import UniversalItemMaster
    from app.models.universal_warehousing import UniversalStockBalance, UniversalStockTransaction
    from app.models.universal_ledger import UniversalInventoryLedger

    async with db_session() as db:
        await db.execute(delete(UniversalInventoryLedger).where(UniversalInventoryLedger.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockTransaction).where(UniversalStockTransaction.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockBalance).where(UniversalStockBalance.tenant_id == tenant_id))
        await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
        await db.execute(delete(OutboxEvent).where(OutboxEvent.tenant_id == tenant_id))
        await db.execute(delete(JournalEntryLine).where(JournalEntryLine.tenant_id == tenant_id))
        await db.execute(delete(JournalVoucher).where(JournalVoucher.tenant_id == tenant_id))
        await db.execute(delete(Account).where(Account.tenant_id == tenant_id))
        await db.execute(delete(AG).where(AG.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


@pytest.mark.asyncio
async def test_finance_adapters_return_plain_schemas_not_orm_objects():
    tenant_id, group_id = await _make_tenant_and_group()
    user_id = await _make_user_account(tenant_id)
    try:
        acc1 = await create_account(tenant_id, group_id, "AT-5100", "Agent Expense", "expense", "Debit")
        acc2 = await create_account(tenant_id, group_id, "AT-1100", "Agent Cash", "asset", "Debit")

        # Returned objects are Pydantic schemas, detached from any session —
        # this is the concrete proof the adapter never leaks an ORM/session
        # object across its public interface.
        from app.schemas.finance_core import AccountOut
        assert isinstance(acc1, AccountOut)
        assert not isinstance(acc1, AsyncSession)

        fetched = await get_account(tenant_id, acc1.id)
        assert fetched.account_code == "AT-5100"

        voucher = await create_and_post_journal_voucher(
            tenant_id=tenant_id,
            user_id=user_id,
            voucher_number="AT-JV-001",
            entry_date="2026-07-12T00:00:00Z",
            lines=[
                {"account_id": acc1.id, "debit": Decimal("100.00"), "credit": Decimal("0.00")},
                {"account_id": acc2.id, "debit": Decimal("0.00"), "credit": Decimal("100.00")},
            ],
        )
        assert voucher.status == "posted"
        assert voucher.total_debit == Decimal("100.00")
    finally:
        await _cleanup(tenant_id)
        await _delete_user_account(user_id)


@pytest.mark.asyncio
async def test_inventory_adapters_stock_movement_atomic():
    tenant_id, _ = await _make_tenant_and_group()
    try:
        item = await create_item(tenant_id, None, item_code="AT-IC1", sku="AT-SKU1", name="Agent Item")
        from app.schemas.universal_inventory import UniversalItemMasterResponse
        assert isinstance(item, UniversalItemMasterResponse)

        async with db_session() as db:
            from app.crud import universal_warehousing as wh_crud
            from app.schemas.universal_warehousing import UniversalWarehouseCreate
            wh = await wh_crud.create_warehouse(db, tenant_id, UniversalWarehouseCreate(name="AT-WH", code="AT-WH"))
            warehouse_id = wh.id

        txn = await execute_stock_movement(
            tenant_id=tenant_id,
            user_id=None,
            item_id=item.id,
            warehouse_id=warehouse_id,
            transaction_type="IN",
            quantity=10,
            reference_type="agent_test",
        )
        from app.schemas.universal_warehousing import StockTransactionResponse
        assert isinstance(txn, StockTransactionResponse)
        assert txn.quantity == 10

        async with db_session() as cleanup_db:
            from sqlalchemy import delete
            from app.models.universal_warehousing import UniversalWarehouse
            await cleanup_db.execute(delete(UniversalWarehouse).where(UniversalWarehouse.id == warehouse_id))
    finally:
        await _cleanup(tenant_id)
