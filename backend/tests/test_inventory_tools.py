"""
tests/test_inventory_tools.py
================================
Calls each app/agent/tools/inventory_tools.py handler directly -- no LLM,
no orchestrator -- with realistic input, against the real database. Same
approach as tests/test_billing_tools.py: app.core.database.db_session()
directly (not the shared rollback-only fixture), since these handlers open
their own real sessions and commit for real.
"""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.agent.tools.inventory_tools import (
    handle_get_stock_balance,
    handle_execute_stock_movement,
    handle_search_item,
)
from app.core.database import db_session
from app.models.tenants import Tenant
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_warehousing import (
    UniversalWarehouse,
    UniversalStockBalance,
    UniversalStockTransaction,
)
from app.models.universal_ledger import UniversalInventoryLedger
from app.models.idempotency import IdempotencyKey

pytestmark = pytest.mark.asyncio


async def _make_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(name="Inventory Tools Test", slug=f"inv-tools-{uuid.uuid4().hex[:10]}", plan="enterprise")
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Main WH", code=f"WH-{uuid.uuid4().hex[:8]}")
        db.add(warehouse)
        await db.flush()
        await db.refresh(warehouse)
        return warehouse.id


async def _make_item(tenant_id: uuid.UUID, name: str = "Inventory Tool Test Item") -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"IT-{uuid.uuid4().hex[:8]}",
            sku=f"IT-SKU-{uuid.uuid4().hex[:8]}", name=name,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(IdempotencyKey).where(IdempotencyKey.tenant_id == tenant_id))
        await db.execute(delete(UniversalInventoryLedger).where(UniversalInventoryLedger.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockTransaction).where(UniversalStockTransaction.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockBalance).where(UniversalStockBalance.tenant_id == tenant_id))
        await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
        await db.execute(delete(UniversalWarehouse).where(UniversalWarehouse.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_get_stock_balance_returns_zero_for_untouched_location():
    tenant_id = await _make_tenant()
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        result = await handle_get_stock_balance(tenant_id=tenant_id, item_id=item_id, warehouse_id=warehouse_id)

        assert result["quantity_on_hand"] == 0.0
        assert result["quantity_reserved"] == 0.0
        assert result["bin_id"] is None
    finally:
        await _cleanup(tenant_id)


async def test_execute_stock_movement_persists_transaction_and_updates_balance():
    tenant_id = await _make_tenant()
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        result = await handle_execute_stock_movement(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=str(uuid.uuid4()),
            item_id=item_id,
            warehouse_id=warehouse_id,
            transaction_type="IN",
            reference_type="test",
            quantity=10.0,
            metadata={"unit_cost": 5.0},
        )

        assert result["transaction_type"] == "IN"
        assert result["quantity"] == 10.0
        # Metadata actually persists now -- see the crud/schema fix in
        # execute_stock_movement/StockTransactionResponse (two masking bugs
        # found while building this tool: the dict key mismatch that
        # silently dropped it, and the alias collision with SQLAlchemy's
        # own Base.metadata that then crashed response serialization once
        # the first was fixed).
        assert result["metadata"] == {"unit_cost": 5.0}

        balance = await handle_get_stock_balance(tenant_id=tenant_id, item_id=item_id, warehouse_id=warehouse_id)
        assert balance["quantity_on_hand"] == 10.0

        async with db_session() as verify_db:
            txn = (await verify_db.execute(
                select(UniversalStockTransaction).where(UniversalStockTransaction.id == uuid.UUID(result["id"]))
            )).scalar_one()
            assert txn.tenant_id == tenant_id
            assert txn.metadata_ == {"unit_cost": 5.0}
    finally:
        await _cleanup(tenant_id)


async def test_execute_stock_movement_negative_stock_raises_validation_error_not_stuck_conflict():
    """See inventory_tools.py's module docstring: business-rule rejections
    (insufficient stock) must surface as a 400 (-> VALIDATION_ERROR in the
    orchestrator), not the HTTP endpoint's 409 -- 409/STUCK_CONFLICT stays
    reserved for the idempotency-claim conflict, so the model can retry
    with a smaller quantity instead of being told to give up."""
    tenant_id = await _make_tenant()
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        with pytest.raises(HTTPException) as exc_info:
            await handle_execute_stock_movement(
                tenant_id=tenant_id,
                user_id=uuid.uuid4(),
                idempotency_key=str(uuid.uuid4()),
                item_id=item_id,
                warehouse_id=warehouse_id,
                transaction_type="OUT",
                reference_type="test",
                quantity=5.0,
            )
        assert exc_info.value.status_code == 400

        async with db_session() as verify_db:
            leaked = (await verify_db.execute(
                select(UniversalStockTransaction).where(UniversalStockTransaction.tenant_id == tenant_id)
            )).scalars().all()
            assert leaked == []
    finally:
        await _cleanup(tenant_id)


async def test_search_item_finds_match_and_stays_tenant_scoped():
    tenant_a = await _make_tenant()
    tenant_b = await _make_tenant()
    await _make_item(tenant_a, name="Widget Assembly Kit")
    await _make_item(tenant_a, name="Unrelated Part")
    await _make_item(tenant_b, name="Widget Assembly International")  # different tenant, similar name
    try:
        result = await handle_search_item(tenant_id=tenant_a, search="Widget")

        assert result["total"] == 1
        names = [i["name"] for i in result["items"]]
        assert names == ["Widget Assembly Kit"]
        assert "Widget Assembly International" not in names
    finally:
        await _cleanup(tenant_a)
        await _cleanup(tenant_b)


# ---------------------------------------------------------------------------
# Idempotency: execute_stock_movement -- same pattern as
# test_billing_tools.py's create_invoice/record_payment idempotency tests:
# two fully independent, sequential handler calls, same key, deliberately
# different (wrong) other arguments on the second call.
# ---------------------------------------------------------------------------

async def test_execute_stock_movement_duplicate_idempotency_key_does_not_double_move_stock():
    tenant_id = await _make_tenant()
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    key = str(uuid.uuid4())
    try:
        first = await handle_execute_stock_movement(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=key,
            item_id=item_id,
            warehouse_id=warehouse_id,
            transaction_type="IN",
            reference_type="test",
            quantity=10.0,
        )

        second = await handle_execute_stock_movement(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=key,
            item_id=item_id,
            warehouse_id=warehouse_id,
            transaction_type="IN",
            reference_type="test-SHOULD-NOT-BE-USED",
            quantity=9999.0,
        )

        assert second == first
        assert second["id"] == first["id"]

        # Sharpest possible proof of no double side-effect: if the second
        # call had actually re-executed, on-hand would be 10 + 9999, not 10.
        balance = await handle_get_stock_balance(tenant_id=tenant_id, item_id=item_id, warehouse_id=warehouse_id)
        assert balance["quantity_on_hand"] == 10.0

        async with db_session() as verify_db:
            txns = (await verify_db.execute(
                select(UniversalStockTransaction).where(UniversalStockTransaction.tenant_id == tenant_id)
            )).scalars().all()
            assert len(txns) == 1

            claim_row = (await verify_db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.endpoint == "agent.execute_stock_movement",
                    IdempotencyKey.key == key,
                )
            )).scalar_one()
            assert claim_row.status == "completed"
            assert str(claim_row.resource_id) == first["id"]
    finally:
        await _cleanup(tenant_id)
