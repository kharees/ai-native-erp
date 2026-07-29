"""
tests/omnichannel_billing/test_invoice_outbox_event.py
===========================================================
Confirms app/services/sales_fulfillment.py's create_invoice_with_stock_
deduction writes an "invoice.created" transactional outbox event
(app/models/outbox.py / app/services/outbox.py) in the SAME atomic
transaction as the invoice itself:
  - a successful invoice creation leaves exactly one matching outbox row,
    with the documented minimum payload fields.
  - a rejected/rolled-back attempt (insufficient stock) leaves NO outbox
    row behind -- the event write shares the exact same db.begin() block
    as the invoice, so if one rolls back, so does the other.

Same real-database pattern as test_atomic_invoice_stock.py.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.core.database import db_session
from app.crud import universal_warehousing as crud_warehousing
from app.models.idempotency import IdempotencyKey
from app.models.outbox import OutboxEvent
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
        tenant = Tenant(name="Outbox Invoice Test", slug=f"outbox-inv-{uuid.uuid4().hex[:10]}", plan="enterprise")
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


async def _make_item(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"OBX-{uuid.uuid4().hex[:8]}",
            sku=f"OBX-SKU-{uuid.uuid4().hex[:8]}", name="Outbox Test Item",
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Outbox Test WH", code=f"OBX-WH-{uuid.uuid4().hex[:8]}")
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


async def _outbox_events(tenant_id: uuid.UUID) -> list[OutboxEvent]:
    async with db_session() as db:
        return list((await db.execute(
            select(OutboxEvent).where(OutboxEvent.tenant_id == tenant_id, OutboxEvent.event_type == "invoice.created")
        )).scalars().all())


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(OutboxEvent).where(OutboxEvent.tenant_id == tenant_id))
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


async def test_successful_invoice_creation_enqueues_exactly_one_invoice_created_event():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        assert await _outbox_events(tenant_id) == []

        payload = UniversalTaxInvoiceCreateWithStock(
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            subtotal=100.0,
            total_amount=100.0,
            items=[{"item_id": str(item_id), "quantity": 2, "unit_price": 50.0, "line_total": 100.0}],
        )
        async with db_session() as db:
            result = await create_invoice_with_stock_deduction(
                db, tenant_id, uuid.uuid4(), payload, str(uuid.uuid4()),
            )

        events = await _outbox_events(tenant_id)
        assert len(events) == 1
        event = events[0]

        assert event.status == "pending"
        assert event.payload["invoice_id"] == result["id"]
        assert event.payload["tenant_id"] == str(tenant_id)
        assert event.payload["customer_id"] == str(customer_id)
        assert Decimal(event.payload["total_amount"]) == Decimal("100.00")
        assert event.payload["invoice_number"] == result["invoice_number"]
        assert event.payload["invoice_number"].startswith("INV/")
        assert "created_at" in event.payload and event.payload["created_at"]
    finally:
        await _cleanup(tenant_id)


async def test_rolled_back_invoice_creation_enqueues_no_outbox_event():
    """Insufficient stock rejects the whole db.begin() block -- the
    outbox write shares that exact transaction, so it must roll back
    right along with the invoice, leaving zero rows behind."""
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 1)  # only 1 in stock
    try:
        payload = UniversalTaxInvoiceCreateWithStock(
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            subtotal=250.0,
            total_amount=250.0,
            items=[{"item_id": str(item_id), "quantity": 5, "unit_price": 50.0, "line_total": 250.0}],
        )
        async with db_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await create_invoice_with_stock_deduction(
                    db, tenant_id, uuid.uuid4(), payload, str(uuid.uuid4()),
                )
        assert exc_info.value.detail["type"] == "insufficient_stock"

        assert await _outbox_events(tenant_id) == []

        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert invoices == []
    finally:
        await _cleanup(tenant_id)
