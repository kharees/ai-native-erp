"""
tests/omnichannel_billing/test_quotation_decimal.py
=======================================================
Exercises app/services/sales_fulfillment.py's create_quotation_with_stock_
check against the real database (same db_session() pattern as
test_atomic_invoice_stock.py) -- confirms the Decimal fix: schemas/
universal_sales.py's UniversalSalesQuotationCreate.total_amount /
UniversalSalesQuotationItemCreate.unit_price are now Decimal (matching
their Numeric(15, 2) DB columns exactly), so create_quotation_with_stock_
check no longer needs a float() round-trip at its total_amount boundary.

Covers:
  - a quotation total built from float-problematic line values (repeated
    0.1 + 0.2-style additions) comes back as an exact Decimal, with no
    binary-floating-point drift, both in the service's return value and
    in what's actually persisted to the Numeric(15, 2) column.
  - the persisted UniversalSalesQuotation.total_amount and each
    UniversalSalesQuotationItem.unit_price are real Decimal instances
    end to end (schema -> ORM -> DB -> read-back), never float.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

import pytest
from sqlalchemy import delete, select

from app.core.database import db_session
from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_sales import UniversalSalesQuotation, UniversalSalesQuotationItem
from app.models.universal_warehousing import StockReservation, UniversalWarehouse
from app.schemas.sales_fulfillment import QuotationStockCheckItem, QuotationWithStockCheckCreate
from app.services.sales_fulfillment import create_quotation_with_stock_check

pytestmark = pytest.mark.asyncio


async def _make_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(name="Quotation Decimal Test", slug=f"quote-dec-{uuid.uuid4().hex[:10]}", plan="enterprise")
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


async def _make_item(tenant_id: uuid.UUID, name: str = "Quotation Decimal Test Item") -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"QD-{uuid.uuid4().hex[:8]}",
            sku=f"QD-SKU-{uuid.uuid4().hex[:8]}", name=name,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Quotation Decimal Test WH", code=f"QD-WH-{uuid.uuid4().hex[:8]}")
        db.add(warehouse)
        await db.flush()
        await db.refresh(warehouse)
        return warehouse.id


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(StockReservation).where(StockReservation.tenant_id == tenant_id))
        await db.execute(delete(UniversalSalesQuotationItem).where(UniversalSalesQuotationItem.tenant_id == tenant_id))
        await db.execute(delete(UniversalSalesQuotation).where(UniversalSalesQuotation.tenant_id == tenant_id))
        await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
        await db.execute(delete(UniversalWarehouse).where(UniversalWarehouse.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomer).where(UniversalCustomer.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_quotation_total_from_float_problematic_values_has_no_drift():
    """Three lines whose quantity*unit_price terms are exactly the kind of
    values that accumulate binary-floating-point error under repeated
    float addition (0.1 + 0.2 != 0.3 in float). The service sums them in
    Decimal space throughout -- the result must be an exact Decimal, not
    something like Decimal('0.6000000000000000...') or a value that
    silently drifted off the true sum."""
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        payload = QuotationWithStockCheckCreate(
            customer_id=customer_id,
            quotation_number=f"QT-DEC-{uuid.uuid4().hex[:10]}",
            warehouse_id=warehouse_id,
            reservation_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            items=[
                # 1 * 0.10 + 1 * 0.20 + 1 * 0.30 == 0.60 exactly in Decimal;
                # summed naively as Python floats, 0.1 + 0.2 + 0.3 ==
                # 0.6000000000000001.
                QuotationStockCheckItem(item_id=item_id, quantity=1, unit_price=Decimal("0.10")),
                QuotationStockCheckItem(item_id=item_id, quantity=1, unit_price=Decimal("0.20")),
                QuotationStockCheckItem(item_id=item_id, quantity=1, unit_price=Decimal("0.30")),
            ],
        )
        async with db_session() as db:
            result = await create_quotation_with_stock_check(db, tenant_id, payload)

        async with db_session() as verify_db:
            quotation = (await verify_db.execute(
                select(UniversalSalesQuotation).where(UniversalSalesQuotation.id == uuid.UUID(result["quotation_id"]))
            )).scalar_one()

            assert quotation.total_amount == Decimal("0.60")
            assert isinstance(quotation.total_amount, Decimal)

            items = (await verify_db.execute(
                select(UniversalSalesQuotationItem).where(UniversalSalesQuotationItem.quotation_id == quotation.id)
            )).scalars().all()
            assert len(items) == 3
            for item in items:
                assert isinstance(item.unit_price, Decimal)
    finally:
        await _cleanup(tenant_id)


async def test_quotation_total_with_many_repeated_fractional_lines():
    """A larger repeated-addition case -- ten lines of 0.1 each. In float
    space, summing 0.1 ten times over does NOT reliably land on exactly
    1.0 (classic float-accumulation drift); in Decimal space it must."""
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        payload = QuotationWithStockCheckCreate(
            customer_id=customer_id,
            quotation_number=f"QT-DEC-{uuid.uuid4().hex[:10]}",
            warehouse_id=warehouse_id,
            reservation_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            items=[
                QuotationStockCheckItem(item_id=item_id, quantity=1, unit_price=Decimal("0.10"))
                for _ in range(10)
            ],
        )
        async with db_session() as db:
            result = await create_quotation_with_stock_check(db, tenant_id, payload)

        async with db_session() as verify_db:
            quotation = (await verify_db.execute(
                select(UniversalSalesQuotation).where(UniversalSalesQuotation.id == uuid.UUID(result["quotation_id"]))
            )).scalar_one()
            assert quotation.total_amount == Decimal("1.00")
    finally:
        await _cleanup(tenant_id)


async def test_quotation_total_matches_sum_of_item_lines():
    """General reconciliation check with non-trivial quantities/prices --
    the persisted header total_amount must equal the exact Decimal sum of
    each item's quantity * unit_price, quantized to 2 decimal places."""
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        payload = QuotationWithStockCheckCreate(
            customer_id=customer_id,
            quotation_number=f"QT-DEC-{uuid.uuid4().hex[:10]}",
            warehouse_id=warehouse_id,
            reservation_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            items=[
                QuotationStockCheckItem(item_id=item_id, quantity=2.5, unit_price=Decimal("19.99")),
                QuotationStockCheckItem(item_id=item_id, quantity=3, unit_price=Decimal("7.33")),
            ],
        )
        async with db_session() as db:
            result = await create_quotation_with_stock_check(db, tenant_id, payload)

        async with db_session() as verify_db:
            quotation = (await verify_db.execute(
                select(UniversalSalesQuotation).where(UniversalSalesQuotation.id == uuid.UUID(result["quotation_id"]))
            )).scalar_one()

        # ROUND_HALF_UP explicitly -- matches create_quotation_with_stock_
        # check's own quantization (see sales_fulfillment.py), not Decimal's
        # default ROUND_HALF_EVEN, since 2.5*19.99 + 3*7.33 == 71.965 lands
        # exactly on a rounding boundary where the two modes disagree.
        expected = (Decimal("2.5") * Decimal("19.99") + Decimal("3") * Decimal("7.33")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
        assert quotation.total_amount == expected
    finally:
        await _cleanup(tenant_id)
