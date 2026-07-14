"""
tests/test_billing_tools.py
=============================
Calls each app/agent/tools/billing_tools.py handler directly -- no LLM,
no orchestrator (none exists yet) -- with realistic input, to confirm
each tool wrapper actually works against the real database before
anything is built on top of it.

Uses app.core.database.db_session() directly (like tests/test_agent_adapters.py
and tests/test_unit_of_work.py) rather than the shared, rollback-only
db_session fixture, because these handlers open their own real sessions
and commit for real -- exercising the actual unit-of-work boundary, not
a simulated one. Each test tears down what it created explicitly.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.agent.tools.billing_tools import (
    handle_create_invoice,
    handle_record_payment,
    handle_search_customer,
)
from app.core.database import db_session
from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_invoices import UniversalTaxInvoice, UniversalTaxInvoiceItem
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_payments import UniversalCustomerWallet, UniversalPaymentReceipt

pytestmark = pytest.mark.asyncio


async def _make_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(name="Billing Tools Test", slug=f"billing-tools-{uuid.uuid4().hex[:10]}", plan="enterprise")
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


async def _make_item(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"BT-{uuid.uuid4().hex[:8]}",
            sku=f"BT-SKU-{uuid.uuid4().hex[:8]}", name="Billing Tool Test Item",
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.tenant_id == tenant_id))
        await db.execute(delete(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id))
        await db.execute(delete(UniversalPaymentReceipt).where(UniversalPaymentReceipt.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomerWallet).where(UniversalCustomerWallet.tenant_id == tenant_id))
        await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomer).where(UniversalCustomer.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_create_invoice_persists_a_real_zero_tax_invoice():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        result = await handle_create_invoice(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            customer_id=customer_id,
            invoice_number=f"BT-INV-{uuid.uuid4().hex[:8]}",
            items=[{"item_id": str(item_id), "quantity": 2, "unit_price": 50.0, "line_total": 100.0}],
            subtotal=100.0,
            total_amount=100.0,
        )

        assert result["customer_id"] == str(customer_id)
        assert result["total_amount"] == 100.0
        # No tax fields in the tool's input -- confirm the persisted
        # record reflects the v1 restriction (zero tax), not silently
        # invented numbers.
        assert result["total_cgst"] == 0.0
        assert result["total_igst"] == 0.0

        async with db_session() as verify_db:
            invoice = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.id == uuid.UUID(result["id"]))
            )).scalar_one()
            assert invoice.tenant_id == tenant_id
            items = (await verify_db.execute(
                select(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.invoice_id == invoice.id)
            )).scalars().all()
            assert len(items) == 1
            assert float(items[0].line_total) == 100.0
    finally:
        await _cleanup(tenant_id)


async def test_create_invoice_rejects_foreign_tenant_customer_and_rolls_back():
    tenant_a = await _make_tenant()
    tenant_b = await _make_tenant()
    customer_in_b = await _make_customer(tenant_b)
    item_id = await _make_item(tenant_a)
    try:
        # Tenant A's tool call references tenant B's customer -- must be
        # rejected (crud.create_tax_invoice's ownership check, Sprint 5 #3),
        # and nothing from this call should persist for either tenant.
        with pytest.raises(HTTPException):
            await handle_create_invoice(
                tenant_id=tenant_a,
                user_id=uuid.uuid4(),
                customer_id=customer_in_b,
                invoice_number=f"BT-INV-{uuid.uuid4().hex[:8]}",
                items=[{"item_id": str(item_id), "quantity": 1, "unit_price": 10.0, "line_total": 10.0}],
            )

        async with db_session() as verify_db:
            leaked = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_a)
            )).scalars().all()
            assert leaked == []
    finally:
        await _cleanup(tenant_a)
        await _cleanup(tenant_b)


async def test_record_payment_persists_receipt_and_credits_wallet():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    try:
        result = await handle_record_payment(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            customer_id=customer_id,
            receipt_number=f"BT-REC-{uuid.uuid4().hex[:8]}",
            payment_mode="BANK",
            amount_received=250.0,
            unallocated_amount=250.0,
        )

        assert result["customer_id"] == str(customer_id)
        assert result["amount_received"] == 250.0

        async with db_session() as verify_db:
            receipt = (await verify_db.execute(
                select(UniversalPaymentReceipt).where(UniversalPaymentReceipt.id == uuid.UUID(result["id"]))
            )).scalar_one()
            assert receipt.tenant_id == tenant_id

            wallet = (await verify_db.execute(
                select(UniversalCustomerWallet).where(
                    UniversalCustomerWallet.customer_id == customer_id,
                    UniversalCustomerWallet.tenant_id == tenant_id,
                )
            )).scalar_one()
            assert wallet.balance == Decimal("250.00")
    finally:
        await _cleanup(tenant_id)


async def test_search_customer_finds_match_and_stays_tenant_scoped():
    tenant_a = await _make_tenant()
    tenant_b = await _make_tenant()
    await _make_customer(tenant_a, name="Widget Traders Ltd")
    await _make_customer(tenant_a, name="Unrelated Co")
    await _make_customer(tenant_b, name="Widget Traders International")  # different tenant, similar name
    try:
        result = await handle_search_customer(tenant_id=tenant_a, search="Widget")

        assert result["total"] == 1
        names = [c["name"] for c in result["items"]]
        assert names == ["Widget Traders Ltd"]
        assert "Widget Traders International" not in names
    finally:
        await _cleanup(tenant_a)
        await _cleanup(tenant_b)
