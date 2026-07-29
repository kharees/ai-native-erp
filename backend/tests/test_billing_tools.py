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
from app.crud import universal_warehousing as crud_warehousing
from app.models.idempotency import IdempotencyKey
from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_invoices import UniversalTaxInvoice, UniversalTaxInvoiceItem
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_ledger import UniversalInventoryLedger
from app.models.universal_payments import UniversalCustomerWallet, UniversalPaymentReceipt
from app.models.universal_warehousing import UniversalStockBalance, UniversalStockTransaction, UniversalWarehouse
from app.schemas.universal_warehousing import StockMovementRequest

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


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Billing Tool Test WH", code=f"BT-WH-{uuid.uuid4().hex[:8]}")
        db.add(warehouse)
        await db.flush()
        await db.refresh(warehouse)
        return warehouse.id


async def _seed_stock(tenant_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID, quantity: float) -> None:
    """create_invoice now deducts real stock (app/services/
    sales_fulfillment.py) -- tests need real on-hand quantity seeded first,
    the same way a real IN movement would."""
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
        await db.execute(delete(UniversalPaymentReceipt).where(UniversalPaymentReceipt.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomerWallet).where(UniversalCustomerWallet.tenant_id == tenant_id))
        await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
        await db.execute(delete(UniversalWarehouse).where(UniversalWarehouse.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomer).where(UniversalCustomer.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_create_invoice_persists_a_real_zero_tax_invoice():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    item_id = await _make_item(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 2)
    try:
        result = await handle_create_invoice(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=str(uuid.uuid4()),
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            items=[{"item_id": str(item_id), "quantity": 2, "unit_price": 50.0, "line_total": 100.0}],
            subtotal=100.0,
            total_amount=100.0,
        )

        assert result["customer_id"] == str(customer_id)
        # Decimal-typed schema fields (see schemas/universal_invoices.py)
        # serialize to JSON strings via model_dump(mode="json") -- Pydantic
        # v2's default for Decimal, deliberate so money never round-trips
        # through a float. Parsed back to Decimal for an exact comparison,
        # not compared as a string literal (which would be just as fragile
        # as a float comparison if the formatting ever changed).
        assert Decimal(result["total_amount"]) == Decimal("100.00")
        # No tax fields in the tool's input -- confirm the persisted
        # record reflects the v1 restriction (zero tax), not silently
        # invented numbers.
        assert Decimal(result["total_cgst"]) == Decimal("0.00")
        assert Decimal(result["total_igst"]) == Decimal("0.00")

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

            # Stock actually deducted -- this is the whole point of the new
            # atomic service (app/services/sales_fulfillment.py): invoice
            # creation and stock deduction are no longer disconnected.
            balance = (await verify_db.execute(
                select(UniversalStockBalance).where(
                    UniversalStockBalance.tenant_id == tenant_id,
                    UniversalStockBalance.item_id == item_id,
                    UniversalStockBalance.warehouse_id == warehouse_id,
                )
            )).scalar_one()
            assert float(balance.quantity_on_hand) == 0.0
    finally:
        await _cleanup(tenant_id)


async def test_create_invoice_rejects_foreign_tenant_customer_and_rolls_back():
    tenant_a = await _make_tenant()
    tenant_b = await _make_tenant()
    customer_in_b = await _make_customer(tenant_b)
    item_id = await _make_item(tenant_a)
    warehouse_id = await _make_warehouse(tenant_a)
    # Enough stock that this test's HTTPException genuinely comes from the
    # customer-ownership check (crud.create_tax_invoice, Sprint 5 #3), not
    # an incidental insufficient-stock rejection from the new pre-check in
    # create_invoice_with_stock_deduction masking a regression here.
    await _seed_stock(tenant_a, item_id, warehouse_id, 10)
    try:
        with pytest.raises(HTTPException):
            await handle_create_invoice(
                tenant_id=tenant_a,
                user_id=uuid.uuid4(),
                idempotency_key=str(uuid.uuid4()),
                customer_id=customer_in_b,
                warehouse_id=warehouse_id,
                items=[{"item_id": str(item_id), "quantity": 1, "unit_price": 10.0, "line_total": 10.0}],
            )

        async with db_session() as verify_db:
            leaked = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_a)
            )).scalars().all()
            assert leaked == []

            # Nothing deducted either -- the whole db.begin() block
            # (availability check + invoice + stock) rolled back together.
            balance = (await verify_db.execute(
                select(UniversalStockBalance).where(
                    UniversalStockBalance.tenant_id == tenant_a,
                    UniversalStockBalance.item_id == item_id,
                    UniversalStockBalance.warehouse_id == warehouse_id,
                )
            )).scalar_one()
            assert float(balance.quantity_on_hand) == 10.0
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
            idempotency_key=str(uuid.uuid4()),
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


async def test_record_payment_failure_after_claim_leaves_no_pending_claim_and_retry_succeeds():
    """Regression test for the idempotency-release fix: a record_payment
    call that fails AFTER claim_idempotency_key succeeds (here, a
    duplicate receipt_number causing a real IntegrityError) must not
    leave the claim stuck "pending" forever -- an immediate retry with
    the same key against a valid payload must succeed."""
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    key = str(uuid.uuid4())
    duplicate_receipt_number = f"BT-DUP-{uuid.uuid4().hex[:8]}"
    try:
        # Pre-existing receipt occupying the receipt_number the first
        # call below will collide with (receipt_number is globally
        # unique -- see app/models/universal_payments.py).
        async with db_session() as db:
            db.add(UniversalPaymentReceipt(
                tenant_id=tenant_id, customer_id=customer_id, receipt_number=duplicate_receipt_number,
                payment_mode="CASH", amount_received=Decimal("10.00"), unallocated_amount=Decimal("0.00"),
            ))
            await db.commit()

        with pytest.raises(Exception):
            await handle_record_payment(
                tenant_id=tenant_id,
                user_id=uuid.uuid4(),
                idempotency_key=key,
                customer_id=customer_id,
                receipt_number=duplicate_receipt_number,
                payment_mode="BANK",
                amount_received=100.0,
                unallocated_amount=100.0,
            )

        async with db_session() as verify_db:
            claim_row = (await verify_db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.endpoint == "agent.record_payment",
                    IdempotencyKey.key == key,
                )
            )).scalar_one_or_none()
            assert claim_row is None, "idempotency claim was left behind after a rejected record_payment call"

        # Retry with the SAME key but a receipt_number that doesn't
        # collide -- must succeed as a fresh request, not a stuck 409.
        result = await handle_record_payment(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=key,
            customer_id=customer_id,
            receipt_number=f"BT-REC-{uuid.uuid4().hex[:8]}",
            payment_mode="BANK",
            amount_received=100.0,
            unallocated_amount=100.0,
        )
        assert result["customer_id"] == str(customer_id)
        assert result["amount_received"] == 100.0
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


# ---------------------------------------------------------------------------
# Idempotency: create_invoice / record_payment
# ---------------------------------------------------------------------------
#
# Each test below makes two fully independent, sequential top-level `await`
# calls to the handler -- not one call reused, not a loop, no shared Python
# state between them beyond the idempotency_key string. Each call opens its
# own db_session() from scratch, exactly as two genuinely separate
# orchestrator invocations would (e.g. an agent retrying a tool call after
# an ambiguous failure). The only thing linking them is the durable
# IdempotencyKey row the first call leaves in the database -- which is
# exactly the real mechanism being tested, not a mock or a shortcut. This
# exercises the actual "second call sees a completed claim and replays"
# code path in app/services/idempotency.py::claim_idempotency_key, not a
# simulation of it.
#
# Not covered here: the *concurrent* conflict path (claim.conflict=True,
# two calls racing while the first is still mid-flight, 409 response).
# That's a distinct scenario from a sequential retry-after-completion, and
# deterministically forcing two calls to race on the same in-flight window
# without artificial delays would make for a flaky test -- not attempted.

async def test_create_invoice_duplicate_idempotency_key_does_not_double_create():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    item_id = await _make_item(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    # Only the first call's quantity (1) is ever really processed -- the
    # second call replays instead of re-executing, so its bogus quantity
    # (99) never reaches stock deduction. See the assertion below.
    await _seed_stock(tenant_id, item_id, warehouse_id, 1)
    key = str(uuid.uuid4())
    try:
        first = await handle_create_invoice(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=key,
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            items=[{"item_id": str(item_id), "quantity": 1, "unit_price": 75.0, "line_total": 75.0}],
            subtotal=75.0,
            total_amount=75.0,
        )

        # Second, fully independent call -- same key, different (bogus)
        # items to prove it's not accidentally re-validating and
        # coincidentally matching; if this executed for real it would
        # either create a second invoice or fail validation differently
        # (there's only 1 unit in stock, and this asks for 99).
        second = await handle_create_invoice(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=key,
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            items=[{"item_id": str(item_id), "quantity": 99, "unit_price": 999.0, "line_total": 98901.0}],
            subtotal=98901.0,
            total_amount=98901.0,
        )

        assert second == first
        assert second["id"] == first["id"]
        assert second["invoice_number"] == first["invoice_number"]

        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert len(invoices) == 1

            claim_row = (await verify_db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.endpoint == "sales.invoice_with_stock_deduction",
                    IdempotencyKey.key == key,
                )
            )).scalar_one()
            assert claim_row.status == "completed"
            assert str(claim_row.resource_id) == first["id"]

            # Sharpest possible proof of no double side-effect: if the
            # second call had actually re-executed, on-hand would be
            # negative or the movement would have raised -- instead it's
            # exactly 1 - 1 = 0, from the first call only.
            balance = (await verify_db.execute(
                select(UniversalStockBalance).where(
                    UniversalStockBalance.tenant_id == tenant_id,
                    UniversalStockBalance.item_id == item_id,
                    UniversalStockBalance.warehouse_id == warehouse_id,
                )
            )).scalar_one()
            assert float(balance.quantity_on_hand) == 0.0
    finally:
        await _cleanup(tenant_id)


async def test_record_payment_duplicate_idempotency_key_does_not_double_create():
    tenant_id = await _make_tenant()
    customer_id = await _make_customer(tenant_id)
    key = str(uuid.uuid4())
    try:
        first = await handle_record_payment(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=key,
            customer_id=customer_id,
            receipt_number=f"BT-REC-{uuid.uuid4().hex[:8]}",
            payment_mode="BANK",
            amount_received=250.0,
            unallocated_amount=250.0,
        )

        second = await handle_record_payment(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            idempotency_key=key,
            customer_id=customer_id,
            receipt_number=f"BT-REC-SHOULD-NOT-BE-USED-{uuid.uuid4().hex[:8]}",
            payment_mode="CASH",
            amount_received=9999.0,
            unallocated_amount=9999.0,
        )

        assert second == first
        assert second["id"] == first["id"]

        async with db_session() as verify_db:
            receipts = (await verify_db.execute(
                select(UniversalPaymentReceipt).where(UniversalPaymentReceipt.tenant_id == tenant_id)
            )).scalars().all()
            assert len(receipts) == 1

            # Sharpest possible proof of no double side-effect: if the
            # second call had actually re-executed, the wallet would show
            # 250 + 9999, not 250.
            wallet = (await verify_db.execute(
                select(UniversalCustomerWallet).where(
                    UniversalCustomerWallet.customer_id == customer_id,
                    UniversalCustomerWallet.tenant_id == tenant_id,
                )
            )).scalar_one()
            assert wallet.balance == Decimal("250.00")

            from app.models.idempotency import IdempotencyKey
            claim_row = (await verify_db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.endpoint == "agent.record_payment",
                    IdempotencyKey.key == key,
                )
            )).scalar_one()
            assert claim_row.status == "completed"
            assert str(claim_row.resource_id) == first["id"]
    finally:
        await _cleanup(tenant_id)
