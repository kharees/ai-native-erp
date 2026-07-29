"""
tests/omnichannel_billing/test_idempotency_release.py
==========================================================
Regression tests for the previously-documented gap in
app/services/sales_fulfillment.py's create_invoice_with_stock_deduction:
a request rejected AFTER claim_idempotency_key succeeded (e.g. the
insufficient_stock HTTPException) used to leave the claim row "pending"
forever, so a legitimate retry with the same key got a permanent 409.

Covers:
  - an insufficient-stock rejection leaves NO pending claim behind, and an
    immediate retry with the same key succeeds once stock is added.
  - a claim that is genuinely still mid-flight (a real "pending" row,
    freshly created) still returns 409 -- release_idempotency_key's stale-
    claim recovery must not accidentally rescue a claim that's still
    legitimately in progress.
  - a stale pending claim older than the 24h TTL can be re-claimed (see
    app/services/idempotency.py's claim_idempotency_key stale-claim
    recovery).

Same real-database pattern as
tests/omnichannel_billing/test_atomic_invoice_stock.py.
"""
import uuid
from datetime import datetime, timedelta, timezone

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

_INVOICE_STOCK_ENDPOINT = "sales.invoice_with_stock_deduction"


async def _make_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(name="Idempotency Release Test", slug=f"idem-release-{uuid.uuid4().hex[:10]}", plan="enterprise")
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
            tenant_id=tenant_id, item_code=f"IDR-{uuid.uuid4().hex[:8]}",
            sku=f"IDR-SKU-{uuid.uuid4().hex[:8]}", name="Idempotency Release Test Item",
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Idempotency Release Test WH", code=f"IDR-WH-{uuid.uuid4().hex[:8]}")
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


async def _get_claim(tenant_id: uuid.UUID, key: str) -> IdempotencyKey | None:
    async with db_session() as db:
        return (await db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.tenant_id == tenant_id,
                IdempotencyKey.endpoint == _INVOICE_STOCK_ENDPOINT,
                IdempotencyKey.key == key,
            )
        )).scalar_one_or_none()


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


def _payload(customer_id: uuid.UUID, warehouse_id: uuid.UUID, item_id: uuid.UUID, quantity: float) -> UniversalTaxInvoiceCreateWithStock:
    return UniversalTaxInvoiceCreateWithStock(
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        subtotal=quantity * 10.0,
        total_amount=quantity * 10.0,
        items=[{"item_id": str(item_id), "quantity": quantity, "unit_price": 10.0, "line_total": quantity * 10.0}],
    )


async def test_insufficient_stock_rejection_leaves_no_pending_claim_and_retry_succeeds():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 1)  # only 1 in stock
    key = str(uuid.uuid4())
    try:
        # First attempt asks for 5 -- only 1 available -> insufficient_stock.
        async with db_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await create_invoice_with_stock_deduction(
                    db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, quantity=5), key,
                )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["type"] == "insufficient_stock"

        # The claim row must be gone entirely -- not stuck "pending".
        claim_row = await _get_claim(tenant_id, key)
        assert claim_row is None, "idempotency claim was left behind after a rejected request"

        # Add enough stock, then retry with the EXACT SAME key -- this must
        # be treated as a fresh request, not a stuck 409, and must succeed.
        await _seed_stock(tenant_id, item_id, warehouse_id, 10)
        async with db_session() as db:
            result = await create_invoice_with_stock_deduction(
                db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, quantity=5), key,
            )
        assert result["id"]

        # And now a completed claim exists, correctly.
        claim_row = await _get_claim(tenant_id, key)
        assert claim_row is not None
        assert claim_row.status == "completed"
    finally:
        await _cleanup(tenant_id)


async def test_genuinely_in_flight_claim_still_returns_409():
    """A real, freshly-created 'pending' claim (simulating another
    request that's genuinely still in progress) must still be rejected
    with 409 -- the stale-claim recovery must not treat every pending
    claim as abandoned, only ones older than the TTL."""
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    key = str(uuid.uuid4())
    try:
        async with db_session() as db:
            db.add(IdempotencyKey(
                tenant_id=tenant_id, endpoint=_INVOICE_STOCK_ENDPOINT, key=key, status="pending",
            ))
            await db.flush()

        async with db_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await create_invoice_with_stock_deduction(
                    db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, quantity=1), key,
                )
        assert exc_info.value.status_code == 409

        # Still there, still pending -- untouched by the failed attempt.
        claim_row = await _get_claim(tenant_id, key)
        assert claim_row is not None
        assert claim_row.status == "pending"

        # No invoice was created.
        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert invoices == []
    finally:
        await _cleanup(tenant_id)


async def test_stale_pending_claim_older_than_ttl_can_be_reclaimed():
    """A pending claim older than the 24h TTL is treated as abandoned
    (e.g. a crash before this fix existed) and gets deleted + re-claimed
    rather than permanently blocking the key."""
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    key = str(uuid.uuid4())
    try:
        stale_created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        async with db_session() as db:
            db.add(IdempotencyKey(
                tenant_id=tenant_id, endpoint=_INVOICE_STOCK_ENDPOINT, key=key, status="pending",
                created_at=stale_created_at,
            ))
            await db.flush()

        async with db_session() as db:
            result = await create_invoice_with_stock_deduction(
                db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, quantity=1), key,
            )
        assert result["id"]

        claim_row = await _get_claim(tenant_id, key)
        assert claim_row is not None
        assert claim_row.status == "completed"

        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert len(invoices) == 1
    finally:
        await _cleanup(tenant_id)
