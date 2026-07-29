"""
tests/test_analytics_tools.py
================================
Calls each app/agent/tools/analytics_tools.py handler directly against
real seeded data -- no LLM, no orchestrator -- confirming every aggregate
is computed correctly by real SQL, not narrated/approximated. Same
approach as tests/test_billing_tools.py: app.core.database.db_session()
directly, real commits, explicit teardown.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.agent.tools.analytics_tools import (
    handle_get_customer_summary,
    handle_get_low_stock_items,
    handle_get_outstanding_dues,
    handle_get_sales_summary,
    handle_get_top_items,
)
from app.core.database import db_session
from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_invoices import UniversalTaxInvoice, UniversalTaxInvoiceItem
from app.models.universal_payments import UniversalPaymentAllocation, UniversalPaymentReceipt
from app.models.universal_warehousing import UniversalStockBalance, UniversalWarehouse

pytestmark = pytest.mark.asyncio


async def _make_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(name="Analytics Tools Test", slug=f"analytics-tools-{uuid.uuid4().hex[:10]}", plan="enterprise")
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant.id


async def _make_customer(tenant_id: uuid.UUID, name: str = "Acme Corp") -> uuid.UUID:
    async with db_session() as db:
        customer = UniversalCustomer(tenant_id=tenant_id, name=name, email=f"{uuid.uuid4().hex[:8]}@example.com")
        db.add(customer)
        await db.flush()
        await db.refresh(customer)
        return customer.id


async def _make_item(tenant_id: uuid.UUID, name: str = "Analytics Test Item") -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"AT-{uuid.uuid4().hex[:8]}",
            sku=f"AT-SKU-{uuid.uuid4().hex[:8]}", name=name,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Analytics Test WH", code=f"AT-WH-{uuid.uuid4().hex[:8]}")
        db.add(warehouse)
        await db.flush()
        await db.refresh(warehouse)
        return warehouse.id


async def _make_invoice(
    tenant_id: uuid.UUID, customer_id: uuid.UUID, total_amount: float,
    status: str = "ISSUED", days_ago: int = 0, items: list[dict] | None = None,
) -> uuid.UUID:
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    async with db_session() as db:
        invoice = UniversalTaxInvoice(
            tenant_id=tenant_id, customer_id=customer_id,
            invoice_number=f"AT-INV-{uuid.uuid4().hex[:8]}", status=status,
            total_amount=total_amount, subtotal=total_amount, created_at=created_at,
        )
        db.add(invoice)
        await db.flush()
        for item in (items or []):
            db.add(UniversalTaxInvoiceItem(tenant_id=tenant_id, invoice_id=invoice.id, **item))
        await db.flush()
        await db.refresh(invoice)
        return invoice.id


async def _make_payment_allocation(tenant_id: uuid.UUID, customer_id: uuid.UUID, invoice_id: uuid.UUID, amount: float) -> None:
    async with db_session() as db:
        receipt = UniversalPaymentReceipt(
            tenant_id=tenant_id, customer_id=customer_id,
            receipt_number=f"AT-REC-{uuid.uuid4().hex[:8]}", payment_mode="BANK",
            amount_received=amount, unallocated_amount=0,
        )
        db.add(receipt)
        await db.flush()
        db.add(UniversalPaymentAllocation(tenant_id=tenant_id, receipt_id=receipt.id, invoice_id=invoice_id, allocated_amount=amount))
        await db.flush()


async def _seed_stock_balance(tenant_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID, on_hand: float, reserved: float = 0, allocated: float = 0) -> None:
    async with db_session() as db:
        db.add(UniversalStockBalance(
            tenant_id=tenant_id, item_id=item_id, warehouse_id=warehouse_id,
            quantity_on_hand=Decimal(str(on_hand)), quantity_reserved=Decimal(str(reserved)),
            quantity_allocated=Decimal(str(allocated)),
        ))
        await db.flush()


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(UniversalPaymentAllocation).where(UniversalPaymentAllocation.tenant_id == tenant_id))
        await db.execute(delete(UniversalPaymentReceipt).where(UniversalPaymentReceipt.tenant_id == tenant_id))
        await db.execute(delete(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.tenant_id == tenant_id))
        await db.execute(delete(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockBalance).where(UniversalStockBalance.tenant_id == tenant_id))
        await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
        await db.execute(delete(UniversalWarehouse).where(UniversalWarehouse.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomer).where(UniversalCustomer.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_get_sales_summary_aggregates_only_issued_invoices_in_range():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    try:
        await _make_invoice(tenant_id, customer_id, 100.0, status="ISSUED", days_ago=5)
        await _make_invoice(tenant_id, customer_id, 200.0, status="ISSUED", days_ago=10)
        # Excluded: DRAFT status.
        await _make_invoice(tenant_id, customer_id, 9999.0, status="DRAFT", days_ago=5)
        # Excluded: outside the date range below.
        await _make_invoice(tenant_id, customer_id, 9999.0, status="ISSUED", days_ago=60)

        result = await handle_get_sales_summary(
            tenant_id=tenant_id,
            date_from=date.today() - timedelta(days=20),
            date_to=date.today(),
        )

        assert result["total_sales_value"] == 300.0
        assert result["invoice_count"] == 2
        assert result["average_invoice_value"] == 150.0
    finally:
        await _cleanup(tenant_id)


async def test_get_top_items_ranks_by_quantity_and_by_value_separately():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    item_high_qty_low_value = await _make_item(tenant_id, name="High Quantity Item")
    item_low_qty_high_value = await _make_item(tenant_id, name="High Value Item")
    try:
        # High quantity, low unit price: 100 units * 1.0 = 100 value.
        await _make_invoice(tenant_id, customer_id, 100.0, items=[
            {"item_id": item_high_qty_low_value, "quantity": 100, "unit_price": 1.0, "line_total": 100.0},
        ])
        # Low quantity, high unit price: 2 units * 500.0 = 1000 value.
        await _make_invoice(tenant_id, customer_id, 1000.0, items=[
            {"item_id": item_low_qty_high_value, "quantity": 2, "unit_price": 500.0, "line_total": 1000.0},
        ])

        result = await handle_get_top_items(
            tenant_id=tenant_id,
            date_from=date.today() - timedelta(days=1),
            date_to=date.today() + timedelta(days=1),
            limit=10,
        )

        assert result["by_quantity"][0]["item_id"] == str(item_high_qty_low_value)
        assert result["by_quantity"][0]["total_quantity"] == 100.0
        assert result["by_value"][0]["item_id"] == str(item_low_qty_high_value)
        assert result["by_value"][0]["total_value"] == 1000.0
    finally:
        await _cleanup(tenant_id)


async def test_get_low_stock_items_uses_available_quantity_not_raw_on_hand():
    tenant_id = await _make_tenant()
    warehouse_id = await _make_warehouse(tenant_id)
    item_low = await _make_item(tenant_id, name="Low Stock Item")
    item_ok = await _make_item(tenant_id, name="Well Stocked Item")
    try:
        # on_hand=10 but reserved=8 + allocated=2 -> available=0 -- at the
        # default threshold (0), this is low even though raw on_hand isn't.
        await _seed_stock_balance(tenant_id, item_low, warehouse_id, on_hand=10, reserved=8, allocated=2)
        await _seed_stock_balance(tenant_id, item_ok, warehouse_id, on_hand=10, reserved=0, allocated=0)

        result = await handle_get_low_stock_items(tenant_id=tenant_id, threshold=None)

        assert result["threshold"] == 0.0
        item_ids = {i["item_id"] for i in result["items"]}
        assert str(item_low) in item_ids
        assert str(item_ok) not in item_ids
        low_row = next(i for i in result["items"] if i["item_id"] == str(item_low))
        assert low_row["available_quantity"] == 0.0
    finally:
        await _cleanup(tenant_id)


async def test_get_low_stock_items_respects_explicit_threshold():
    tenant_id = await _make_tenant()
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        await _seed_stock_balance(tenant_id, item_id, warehouse_id, on_hand=5)

        # available=5 is above the default 0 threshold, but at/below an
        # explicit threshold of 5.
        below_default = await handle_get_low_stock_items(tenant_id=tenant_id, threshold=None)
        assert str(item_id) not in {i["item_id"] for i in below_default["items"]}

        at_explicit_threshold = await handle_get_low_stock_items(tenant_id=tenant_id, threshold=5)
        assert str(item_id) in {i["item_id"] for i in at_explicit_threshold["items"]}
    finally:
        await _cleanup(tenant_id)


async def test_get_outstanding_dues_computes_balance_and_aging_buckets():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    try:
        # 10 days old, fully unpaid -> 0-30 bucket, balance_due=100.
        recent_unpaid = await _make_invoice(tenant_id, customer_id, 100.0, days_ago=10)
        # 45 days old, partially paid -> 31-60 bucket, balance_due=150.
        mid_partial = await _make_invoice(tenant_id, customer_id, 200.0, days_ago=45)
        await _make_payment_allocation(tenant_id, customer_id, mid_partial, 50.0)
        # 100 days old, fully paid -> excluded entirely (balance_due<=0).
        old_paid = await _make_invoice(tenant_id, customer_id, 300.0, days_ago=100)
        await _make_payment_allocation(tenant_id, customer_id, old_paid, 300.0)

        result = await handle_get_outstanding_dues(tenant_id=tenant_id, customer_id=None)

        invoices_by_id = {i["invoice_id"]: i for i in result["invoices"]}
        assert str(recent_unpaid) in invoices_by_id
        assert str(mid_partial) in invoices_by_id
        assert str(old_paid) not in invoices_by_id

        assert invoices_by_id[str(recent_unpaid)]["balance_due"] == 100.0
        assert invoices_by_id[str(recent_unpaid)]["aging_bucket"] == "0-30"
        assert invoices_by_id[str(mid_partial)]["balance_due"] == 150.0
        assert invoices_by_id[str(mid_partial)]["aging_bucket"] == "31-60"

        assert result["total_outstanding"] == 250.0
        assert result["aging_buckets"]["0-30"] == 100.0
        assert result["aging_buckets"]["31-60"] == 150.0
    finally:
        await _cleanup(tenant_id)


async def test_get_outstanding_dues_filters_by_customer():
    tenant_id = await _make_tenant()
    customer_a = await _make_customer(tenant_id, name="Customer A")
    customer_b = await _make_customer(tenant_id, name="Customer B")
    try:
        await _make_invoice(tenant_id, customer_a, 100.0, days_ago=5)
        await _make_invoice(tenant_id, customer_b, 200.0, days_ago=5)

        result = await handle_get_outstanding_dues(tenant_id=tenant_id, customer_id=customer_a)

        assert len(result["invoices"]) == 1
        assert result["invoices"][0]["customer_id"] == str(customer_a)
        assert result["total_outstanding"] == 100.0
    finally:
        await _cleanup(tenant_id)


async def test_get_customer_summary_aggregates_spend_and_payment_status():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    other_customer_id = await _make_customer(tenant_id, name="Someone Else")
    try:
        inv1 = await _make_invoice(tenant_id, customer_id, 100.0, days_ago=5)
        await _make_payment_allocation(tenant_id, customer_id, inv1, 100.0)  # fully paid
        inv2 = await _make_invoice(tenant_id, customer_id, 200.0, days_ago=10)
        await _make_payment_allocation(tenant_id, customer_id, inv2, 50.0)  # partially paid
        # Different customer -- must not leak into this customer's summary.
        await _make_invoice(tenant_id, other_customer_id, 9999.0, days_ago=5)
        # Outside the date range below.
        await _make_invoice(tenant_id, customer_id, 9999.0, days_ago=60)

        result = await handle_get_customer_summary(
            tenant_id=tenant_id, customer_id=customer_id,
            date_from=date.today() - timedelta(days=20), date_to=date.today(),
        )

        assert result["order_count"] == 2
        assert result["total_spend"] == 300.0
        assert result["total_paid"] == 150.0
        assert result["total_outstanding"] == 150.0

        orders_by_id = {o["invoice_id"]: o for o in result["orders"]}
        assert orders_by_id[str(inv1)]["balance_due"] == 0.0
        assert orders_by_id[str(inv2)]["balance_due"] == 150.0
    finally:
        await _cleanup(tenant_id)
