"""
tests/omnichannel_billing/test_atomic_invoice_stock.py
==========================================================
Exercises app/services/sales_fulfillment.py's
create_invoice_with_stock_deduction against the real database (like
tests/test_billing_tools.py, tests/test_inventory_tools.py) -- invoice
creation and stock deduction used to be completely disconnected; this
proves they're now atomic: one line's insufficient stock rolls back the
whole invoice (not a partial one), a retried idempotency key doesn't
double-deduct, and two genuinely concurrent requests for the same last
unit of stock don't both succeed.

The concurrency test opens two separate db_session()s and runs both calls
via asyncio.gather -- two real connections racing on the same
UniversalStockBalance row, not a simulation. Protection against that race
comes from execute_stock_movement's own row-level lock
(_get_or_create_balance_locked's SELECT ... FOR UPDATE), not from
create_invoice_with_stock_deduction's own pre-check (a deliberate,
documented TOCTOU gap in the pre-check alone -- see that function's
docstring in sales_fulfillment.py).
"""
import asyncio
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.core.database import db_session
from app.crud import universal_warehousing as crud_warehousing
from app.models.idempotency import IdempotencyKey
from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_invoices import UniversalTaxInvoice, UniversalTaxInvoiceItem
from app.models.universal_ledger import UniversalInventoryLedger
from app.models.universal_warehousing import UniversalStockBalance, UniversalStockTransaction, UniversalWarehouse
from app.schemas.universal_invoices import UniversalTaxInvoiceCreateWithStock
from app.schemas.universal_warehousing import StockMovementRequest
from app.services.sales_fulfillment import create_invoice_with_stock_deduction

pytestmark = pytest.mark.asyncio


async def _make_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(name="Atomic Invoice Stock Test", slug=f"atomic-inv-{uuid.uuid4().hex[:10]}", plan="enterprise")
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant.id


async def _make_customer(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        customer = UniversalCustomer(tenant_id=tenant_id, name="Acme Corp", email=f"{uuid.uuid4().hex[:8]}@example.com")
        db.add(customer)
        await db.flush()
        await db.refresh(customer)
        return customer.id


async def _make_item(tenant_id: uuid.UUID, name: str = "Atomic Test Item") -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"AIS-{uuid.uuid4().hex[:8]}",
            sku=f"AIS-SKU-{uuid.uuid4().hex[:8]}", name=name,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Atomic Test WH", code=f"AIS-WH-{uuid.uuid4().hex[:8]}")
        db.add(warehouse)
        await db.flush()
        await db.refresh(warehouse)
        return warehouse.id


async def _seed_stock(tenant_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID, quantity: float) -> None:
    async with db_session() as db:
        await crud_warehousing.execute_stock_movement(
            db, tenant_id, None,
            StockMovementRequest(
                item_id=item_id, warehouse_id=warehouse_id, transaction_type="IN",
                reference_type="test_seed", quantity=quantity,
            ),
        )


async def _on_hand(tenant_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID) -> float:
    async with db_session() as db:
        balance = (await db.execute(
            select(UniversalStockBalance).where(
                UniversalStockBalance.tenant_id == tenant_id,
                UniversalStockBalance.item_id == item_id,
                UniversalStockBalance.warehouse_id == warehouse_id,
            )
        )).scalar_one()
        return float(balance.quantity_on_hand)


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(IdempotencyKey).where(IdempotencyKey.tenant_id == tenant_id))
        await db.execute(delete(UniversalInventoryLedger).where(UniversalInventoryLedger.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockTransaction).where(UniversalStockTransaction.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockBalance).where(UniversalStockBalance.tenant_id == tenant_id))
        await db.execute(delete(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.tenant_id == tenant_id))
        await db.execute(delete(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id))
        await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
        await db.execute(delete(UniversalWarehouse).where(UniversalWarehouse.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomer).where(UniversalCustomer.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_invoice_rolls_back_fully_when_one_line_lacks_stock():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_ok = await _make_item(tenant_id, name="Well Stocked Item")
    item_short = await _make_item(tenant_id, name="Short Item")
    await _seed_stock(tenant_id, item_ok, warehouse_id, 10)
    await _seed_stock(tenant_id, item_short, warehouse_id, 1)
    try:
        payload = UniversalTaxInvoiceCreateWithStock(
            customer_id=customer_id,
            invoice_number=f"AIS-INV-{uuid.uuid4().hex[:8]}",
            warehouse_id=warehouse_id,
            subtotal=150.0,
            total_amount=150.0,
            items=[
                {"item_id": str(item_ok), "quantity": 5, "unit_price": 10.0, "line_total": 50.0},
                # Only 1 unit in stock, invoice asks for 5 -- this line is short.
                {"item_id": str(item_short), "quantity": 5, "unit_price": 20.0, "line_total": 100.0},
            ],
        )

        async with db_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await create_invoice_with_stock_deduction(
                    db, tenant_id, uuid.uuid4(), payload, str(uuid.uuid4())
                )

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["type"] == "insufficient_stock"
        short_item_ids = {si["item_id"] for si in detail["short_items"]}
        assert str(item_short) in short_item_ids
        # The well-stocked line must NOT appear -- only the genuinely short
        # line is reported.
        assert str(item_ok) not in short_item_ids

        # Nothing persisted -- not the invoice, and not even the item that
        # had enough stock (proving the whole transaction rolled back, not
        # just the short line).
        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert invoices == []

        assert await _on_hand(tenant_id, item_ok, warehouse_id) == 10.0
        assert await _on_hand(tenant_id, item_short, warehouse_id) == 1.0
    finally:
        await _cleanup(tenant_id)


async def test_retried_idempotency_key_does_not_double_deduct():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 5)
    key = str(uuid.uuid4())
    try:
        payload = UniversalTaxInvoiceCreateWithStock(
            customer_id=customer_id,
            invoice_number=f"AIS-INV-{uuid.uuid4().hex[:8]}",
            warehouse_id=warehouse_id,
            subtotal=30.0,
            total_amount=30.0,
            items=[{"item_id": str(item_id), "quantity": 3, "unit_price": 10.0, "line_total": 30.0}],
        )

        async with db_session() as db:
            first = await create_invoice_with_stock_deduction(db, tenant_id, uuid.uuid4(), payload, key)

        # Second, fully independent call -- same key, same payload object
        # is fine here since the point is proving idempotency, not
        # argument-tampering (that's covered in test_billing_tools.py).
        async with db_session() as db:
            second = await create_invoice_with_stock_deduction(db, tenant_id, uuid.uuid4(), payload, key)

        assert second == first
        assert second["id"] == first["id"]

        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert len(invoices) == 1

        # Sharpest possible proof of no double side-effect: if the second
        # call had actually re-executed, on-hand would be 5 - 3 - 3 = -1
        # (or it would have raised insufficient_stock instead of
        # replaying) -- instead it's exactly 5 - 3 = 2, from the first
        # call only.
        assert await _on_hand(tenant_id, item_id, warehouse_id) == 2.0
    finally:
        await _cleanup(tenant_id)


async def test_concurrent_invoice_creation_for_last_unit_does_not_double_sell():
    """Two genuinely concurrent requests (separate sessions, separate
    idempotency keys -- a real stock race, not an idempotency replay) for
    the same single unit of stock: exactly one succeeds, the other is
    rejected, and on-hand never goes negative. Protection comes from
    execute_stock_movement's row-level lock, not the pre-check -- see
    module docstring."""
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 1)
    try:
        def _make_payload(invoice_number: str) -> UniversalTaxInvoiceCreateWithStock:
            return UniversalTaxInvoiceCreateWithStock(
                customer_id=customer_id,
                invoice_number=invoice_number,
                warehouse_id=warehouse_id,
                subtotal=10.0,
                total_amount=10.0,
                items=[{"item_id": str(item_id), "quantity": 1, "unit_price": 10.0, "line_total": 10.0}],
            )

        async def _attempt(invoice_number: str):
            async with db_session() as db:
                return await create_invoice_with_stock_deduction(
                    db, tenant_id, uuid.uuid4(), _make_payload(invoice_number), str(uuid.uuid4())
                )

        results = await asyncio.gather(
            _attempt(f"AIS-RACE-A-{uuid.uuid4().hex[:8]}"),
            _attempt(f"AIS-RACE-B-{uuid.uuid4().hex[:8]}"),
            return_exceptions=True,
        )

        successes = [r for r in results if not isinstance(r, BaseException)]
        failures = [r for r in results if isinstance(r, BaseException)]

        assert len(successes) == 1, f"expected exactly 1 success, got {len(successes)}: {results}"
        assert len(failures) == 1, f"expected exactly 1 failure, got {len(failures)}: {results}"
        assert isinstance(failures[0], HTTPException)
        assert failures[0].status_code == 400
        assert failures[0].detail["type"] == "insufficient_stock"

        # Never negative, never double-sold.
        assert await _on_hand(tenant_id, item_id, warehouse_id) == 0.0

        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert len(invoices) == 1
    finally:
        await _cleanup(tenant_id)
