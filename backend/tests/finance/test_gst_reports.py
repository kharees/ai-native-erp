"""
tests/finance/test_gst_reports.py
=====================================
Exercises app/services/gst_reports.py directly against the real database
(same db_session() pattern as tests/omnichannel_billing/
test_gst_invoice_compliance.py) -- invoices are created through the real
create_invoice_with_stock_deduction path so CGST/SGST/IGST are genuinely
computed by app/services/gst_compliance.py, not hand-set, before the
report aggregates them.

Covers:
  - B2B vs B2C classification is driven by whether the customer carries a
    GSTIN (universal_customers.gst_number).
  - the HSN-wise summary's totals match the sum of the invoice line items
    that carry each HSN code.
  - GSTR-3B's totals reconcile exactly with the sum of GSTR-1's B2B +
    B2CL + B2CS sections for the same period.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete

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
from app.services import gst_reports
from app.services.gst_compliance import get_current_financial_year
from app.services.sales_fulfillment import create_invoice_with_stock_deduction

pytestmark = pytest.mark.asyncio

_FY = get_current_financial_year(date.today())
_MONTH = date.today().month


async def _make_tenant(state_code: str = "27") -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(
            name="GST Report Test Seller", slug=f"gst-report-{uuid.uuid4().hex[:10]}", plan="enterprise",
            gstin=f"{state_code}AAAAA0000A1Z5", legal_name="GST Report Test Seller Pvt Ltd", state_code=state_code,
        )
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant.id


async def _make_customer(tenant_id: uuid.UUID, state_code: str | None, gst_number: str | None = None) -> uuid.UUID:
    async with db_session() as db:
        customer = UniversalCustomer(
            tenant_id=tenant_id, name="Report Buyer Co", email=f"{uuid.uuid4().hex[:8]}@example.com",
            state_code=state_code, gst_number=gst_number,
        )
        db.add(customer)
        await db.flush()
        await db.refresh(customer)
        return customer.id


async def _make_item(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"GSTR-{uuid.uuid4().hex[:8]}",
            sku=f"GSTR-SKU-{uuid.uuid4().hex[:8]}", name="GST Report Test Item",
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="GSTR Test WH", code=f"GSTR-WH-{uuid.uuid4().hex[:8]}")
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


async def _create_invoice(
    tenant_id, customer_id, warehouse_id, item_id,
    quantity=1, unit_price=100.0, tax_amount=18.0, hsn_sac_code="1234",
):
    quantity_dec = Decimal(str(quantity))
    unit_price_dec = Decimal(str(unit_price))
    tax_amount_dec = Decimal(str(tax_amount))
    line_total = quantity_dec * unit_price_dec + tax_amount_dec
    payload = UniversalTaxInvoiceCreateWithStock(
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        subtotal=quantity_dec * unit_price_dec,
        total_amount=line_total,
        items=[{
            "item_id": str(item_id), "hsn_sac_code": hsn_sac_code, "quantity": quantity,
            "unit_price": unit_price_dec,
            "cgst_amount": tax_amount_dec, "sgst_amount": Decimal("0.00"), "igst_amount": Decimal("0.00"),
            "line_total": line_total,
        }],
    )
    async with db_session() as db:
        return await create_invoice_with_stock_deduction(
            db, tenant_id, uuid.uuid4(), payload, str(uuid.uuid4()),
        )


async def test_gstr1_classifies_registered_customer_as_b2b():
    """A customer with a GSTIN must land in B2B, never B2CS/B2CL, and the
    row's tax figures must match the invoice exactly."""
    tenant_id = await _make_tenant(state_code="27")
    customer_id = await _make_customer(tenant_id, state_code="27", gst_number="27BBBBB0000B1Z1")
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        result = await _create_invoice(tenant_id, customer_id, warehouse_id, item_id, tax_amount=18.0)

        async with db_session() as db:
            data = await gst_reports.generate_gstr1_data(db, tenant_id, _FY, _MONTH)

        assert data["b2cs"] == []
        assert data["b2cl"] == []
        assert len(data["b2b"]) == 1
        row = data["b2b"][0]
        assert row["gstin"] == "27BBBBB0000B1Z1"
        assert row["invoice_number"] == result["invoice_number"]
        assert Decimal(str(row["cgst_amount"])) == Decimal("9.00")
        assert Decimal(str(row["sgst_amount"])) == Decimal("9.00")
        assert Decimal(str(row["igst_amount"])) == Decimal("0.00")
    finally:
        await _cleanup(tenant_id)


async def test_gstr1_classifies_unregistered_small_customer_as_b2cs():
    """No GSTIN and below the B2C-Large threshold -> aggregated into
    B2CS by (place of supply, rate), not reported invoice-wise."""
    tenant_id = await _make_tenant(state_code="27")
    customer_id = await _make_customer(tenant_id, state_code="27", gst_number=None)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        await _create_invoice(tenant_id, customer_id, warehouse_id, item_id, tax_amount=18.0)

        async with db_session() as db:
            data = await gst_reports.generate_gstr1_data(db, tenant_id, _FY, _MONTH)

        assert data["b2b"] == []
        assert data["b2cl"] == []
        assert len(data["b2cs"]) == 1
        bucket = data["b2cs"][0]
        assert Decimal(str(bucket["cgst_amount"])) == Decimal("9.00")
        assert Decimal(str(bucket["sgst_amount"])) == Decimal("9.00")
        assert bucket["invoice_count"] == 1
    finally:
        await _cleanup(tenant_id)


async def test_gstr1_classifies_unregistered_large_interstate_customer_as_b2cl():
    """No GSTIN, inter-state, invoice value above the Rs 2,50,000
    threshold -> reported invoice-wise in B2CL, not folded into B2CS."""
    tenant_id = await _make_tenant(state_code="27")
    customer_id = await _make_customer(tenant_id, state_code="29", gst_number=None)  # Karnataka -- inter-state
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        result = await _create_invoice(
            tenant_id, customer_id, warehouse_id, item_id,
            unit_price=300000.0, tax_amount=54000.0,
        )

        async with db_session() as db:
            data = await gst_reports.generate_gstr1_data(db, tenant_id, _FY, _MONTH)

        assert data["b2b"] == []
        assert data["b2cs"] == []
        assert len(data["b2cl"]) == 1
        row = data["b2cl"][0]
        assert row["invoice_number"] == result["invoice_number"]
        assert Decimal(str(row["igst_amount"])) == Decimal("54000.00")
    finally:
        await _cleanup(tenant_id)


async def test_gstr1_hsn_summary_matches_invoice_line_items():
    """Two invoices carrying the same HSN code -- the HSN summary bucket
    for that code must equal the sum of both invoices' line-item taxable
    value and tax amounts exactly."""
    tenant_id = await _make_tenant(state_code="27")
    customer_id = await _make_customer(tenant_id, state_code="27", gst_number="27BBBBB0000B1Z1")
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        await _create_invoice(tenant_id, customer_id, warehouse_id, item_id, quantity=1, unit_price=100.0, tax_amount=18.0, hsn_sac_code="6109")
        await _create_invoice(tenant_id, customer_id, warehouse_id, item_id, quantity=2, unit_price=50.0, tax_amount=18.0, hsn_sac_code="6109")

        async with db_session() as db:
            data = await gst_reports.generate_gstr1_data(db, tenant_id, _FY, _MONTH)

        assert len(data["hsn_summary"]) == 1
        bucket = data["hsn_summary"][0]
        assert bucket["hsn_sac_code"] == "6109"
        # taxable value: (1*100) + (2*50) = 200; tax: 18 + 18 = 36 (all CGST+SGST, intra-state)
        assert Decimal(str(bucket["taxable_value"])) == Decimal("200.00")
        assert Decimal(str(bucket["cgst_amount"])) == Decimal("18.00")
        assert Decimal(str(bucket["sgst_amount"])) == Decimal("18.00")
        assert Decimal(str(bucket["total_value"])) == Decimal("236.00")
    finally:
        await _cleanup(tenant_id)


async def test_gstr3b_reconciles_with_gstr1_sections():
    """GSTR-3B's totals must equal the sum of GSTR-1's B2B + B2CL + B2CS
    sections for the identical tenant/period -- every invoice falls into
    exactly one of those three buckets, so summing across them must land
    on GSTR-3B's totals exactly, not approximately."""
    tenant_id = await _make_tenant(state_code="27")
    b2b_customer = await _make_customer(tenant_id, state_code="27", gst_number="27BBBBB0000B1Z1")
    b2cs_customer = await _make_customer(tenant_id, state_code="27", gst_number=None)
    b2cl_customer = await _make_customer(tenant_id, state_code="29", gst_number=None)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 30)
    try:
        await _create_invoice(tenant_id, b2b_customer, warehouse_id, item_id, tax_amount=18.0)
        await _create_invoice(tenant_id, b2cs_customer, warehouse_id, item_id, tax_amount=20.0)
        await _create_invoice(tenant_id, b2cl_customer, warehouse_id, item_id, unit_price=300000.0, tax_amount=54000.0)

        async with db_session() as db:
            gstr1 = await gst_reports.generate_gstr1_data(db, tenant_id, _FY, _MONTH)
        async with db_session() as db:
            gstr3b = await gst_reports.generate_gstr3b_summary(db, tenant_id, _FY, _MONTH)

        def _sum(rows, key):
            return sum(Decimal(str(r[key])) for r in rows)

        combined_taxable = (
            _sum(gstr1["b2b"], "taxable_value") + _sum(gstr1["b2cl"], "taxable_value") + _sum(gstr1["b2cs"], "taxable_value")
        )
        combined_cgst = (
            _sum(gstr1["b2b"], "cgst_amount") + _sum(gstr1["b2cl"], "cgst_amount") + _sum(gstr1["b2cs"], "cgst_amount")
        )
        combined_sgst = (
            _sum(gstr1["b2b"], "sgst_amount") + _sum(gstr1["b2cl"], "sgst_amount") + _sum(gstr1["b2cs"], "sgst_amount")
        )
        combined_igst = (
            _sum(gstr1["b2b"], "igst_amount") + _sum(gstr1["b2cl"], "igst_amount") + _sum(gstr1["b2cs"], "igst_amount")
        )

        assert Decimal(str(gstr3b["total_taxable_value"])) == combined_taxable
        assert Decimal(str(gstr3b["total_cgst"])) == combined_cgst
        assert Decimal(str(gstr3b["total_sgst"])) == combined_sgst
        assert Decimal(str(gstr3b["total_igst"])) == combined_igst
        assert gstr3b["invoice_count"] == 3
    finally:
        await _cleanup(tenant_id)
