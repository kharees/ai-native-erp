"""
tests/omnichannel_billing/test_gst_invoice_compliance.py
============================================================
Exercises the GST legal-compliance wiring added to
app/services/sales_fulfillment.py's create_invoice_with_stock_deduction
and app/crud/universal_numbering.py's generate_next_number, against the
real database (same pattern as test_atomic_invoice_stock.py).

Covers:
  - intra-state invoices (seller/buyer share a GST state code) split the
    line's total tax into CGST + SGST, never IGST.
  - inter-state invoices (different state codes) use IGST only.
  - invoice numbers are gapless and never duplicate under real concurrent
    creation -- generate_next_number's row lock (SELECT ... FOR UPDATE)
    serializes concurrent callers, and because the increment lives inside
    the same db.begin() block as the invoice it numbers, a rolled-back
    attempt never burns a number.
  - composition-scheme tenants never generate itemized CGST/SGST/IGST,
    regardless of what the caller's payload asked for.

Pure-logic behavior of app/services/gst_compliance.py itself (no DB
involved) is covered separately in tests/test_gst_compliance.py.
"""
import asyncio
import uuid
from decimal import Decimal

import pytest
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


async def _make_tenant(
    state_code: str = "27", gstin: str = "27AAAAA0000A1Z5", composition_scheme: bool = False,
) -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(
            name="GST Test Seller", slug=f"gst-seller-{uuid.uuid4().hex[:10]}", plan="enterprise",
            gstin=gstin, legal_name="GST Test Seller Pvt Ltd", state_code=state_code,
            composition_scheme=composition_scheme,
        )
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant.id


async def _make_customer(tenant_id: uuid.UUID, state_code: str | None, gst_number: str | None = None) -> uuid.UUID:
    async with db_session() as db:
        customer = UniversalCustomer(
            tenant_id=tenant_id, name="Buyer Co", email=f"{uuid.uuid4().hex[:8]}@example.com",
            state_code=state_code, gst_number=gst_number,
        )
        db.add(customer)
        await db.flush()
        await db.refresh(customer)
        return customer.id


async def _make_item(tenant_id: uuid.UUID, name: str = "GST Test Item") -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"GST-{uuid.uuid4().hex[:8]}",
            sku=f"GST-SKU-{uuid.uuid4().hex[:8]}", name=name,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="GST Test WH", code=f"GST-WH-{uuid.uuid4().hex[:8]}")
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


def _payload(customer_id, warehouse_id, item_id, quantity=1, unit_price=100.0, tax_amount=18.0):
    """tax_amount is split across the item's cgst/sgst/igst fields exactly
    as a caller might naively fill them in -- create_invoice_with_stock_
    deduction is expected to discard this split entirely and recompute it
    from place of supply (or zero it for composition tenants), so the
    exact distribution here shouldn't matter to the assertions.

    unit_price/tax_amount arrive as plain float literals (callers write
    `tax_amount=33.33`, not `Decimal("33.33")`) -- lifted into Decimal via
    their exact string representation before any arithmetic, same
    Decimal(str(x)) convention app/services/sales_fulfillment.py itself
    uses. Computing line_total as `quantity * unit_price + tax_amount` in
    float space (as this helper originally did) is exactly the bug this
    whole module exists to catch: 100.0 + 33.33 == 133.32999999999998 in
    binary floating point, which then fails schema validation outright
    (decimal_max_digits) rather than silently rounding -- a real
    demonstration of the float-drift class of bug, caught here in test
    setup instead of in application code.
    """
    quantity_dec = Decimal(str(quantity))
    unit_price_dec = Decimal(str(unit_price))
    tax_amount_dec = Decimal(str(tax_amount))
    line_total = quantity_dec * unit_price_dec + tax_amount_dec
    return UniversalTaxInvoiceCreateWithStock(
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        subtotal=quantity_dec * unit_price_dec,
        total_amount=line_total,
        items=[{
            "item_id": str(item_id), "quantity": quantity, "unit_price": unit_price_dec,
            "cgst_amount": tax_amount_dec, "sgst_amount": Decimal("0.00"), "igst_amount": Decimal("0.00"),
            "line_total": line_total,
        }],
    )


async def test_intra_state_invoice_splits_cgst_and_sgst():
    """Seller and buyer share GST state code 27 (Maharashtra) -- the
    invoice must carry CGST+SGST, split exactly in half, and zero IGST."""
    tenant_id = await _make_tenant(state_code="27")
    customer_id = await _make_customer(tenant_id, state_code="27")
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        async with db_session() as db:
            result = await create_invoice_with_stock_deduction(
                db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, tax_amount=18.0),
                str(uuid.uuid4()),
            )

        # UniversalTaxInvoiceResponse's Decimal fields serialize to JSON
        # strings (Pydantic v2's default for Decimal, via model_dump(mode=
        # "json")) -- parsed back to Decimal for an exact comparison rather
        # than compared against a float literal.
        assert Decimal(result["total_cgst"]) == Decimal("9.00")
        assert Decimal(result["total_sgst"]) == Decimal("9.00")
        assert Decimal(result["total_igst"]) == Decimal("0.00")

        async with db_session() as verify_db:
            item_row = (await verify_db.execute(
                select(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.invoice_id == uuid.UUID(result["id"]))
            )).scalar_one()
            assert item_row.cgst_amount == Decimal("9.00")
            assert item_row.sgst_amount == Decimal("9.00")
            assert item_row.igst_amount == Decimal("0.00")
    finally:
        await _cleanup(tenant_id)


async def test_inter_state_invoice_uses_igst():
    """Seller in Maharashtra (27), buyer in Karnataka (29) -- inter-state,
    so the full tax amount must land entirely in IGST with CGST/SGST at
    zero."""
    tenant_id = await _make_tenant(state_code="27")
    customer_id = await _make_customer(tenant_id, state_code="29")
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        async with db_session() as db:
            result = await create_invoice_with_stock_deduction(
                db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, tax_amount=18.0),
                str(uuid.uuid4()),
            )

        assert Decimal(result["total_igst"]) == Decimal("18.00")
        assert Decimal(result["total_cgst"]) == Decimal("0.00")
        assert Decimal(result["total_sgst"]) == Decimal("0.00")

        async with db_session() as verify_db:
            item_row = (await verify_db.execute(
                select(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.invoice_id == uuid.UUID(result["id"]))
            )).scalar_one()
            assert item_row.igst_amount == Decimal("18.00")
            assert item_row.cgst_amount == Decimal("0.00")
            assert item_row.sgst_amount == Decimal("0.00")
    finally:
        await _cleanup(tenant_id)


async def test_composition_scheme_tenant_generates_no_itemized_gst():
    """A composition-scheme tenant must never itemize CGST/SGST/IGST on an
    invoice -- even though this payload asks for tax_amount=18.0 exactly
    like the two tests above, every tax field must come back zero."""
    tenant_id = await _make_tenant(state_code="27", composition_scheme=True)
    customer_id = await _make_customer(tenant_id, state_code="27")  # same state -- would be CGST+SGST if not composition
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        async with db_session() as db:
            result = await create_invoice_with_stock_deduction(
                db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, tax_amount=18.0),
                str(uuid.uuid4()),
            )

        assert Decimal(result["total_cgst"]) == Decimal("0.00")
        assert Decimal(result["total_sgst"]) == Decimal("0.00")
        assert Decimal(result["total_igst"]) == Decimal("0.00")

        async with db_session() as verify_db:
            item_row = (await verify_db.execute(
                select(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.invoice_id == uuid.UUID(result["id"]))
            )).scalar_one()
            assert item_row.cgst_amount == Decimal("0.00")
            assert item_row.sgst_amount == Decimal("0.00")
            assert item_row.igst_amount == Decimal("0.00")
    finally:
        await _cleanup(tenant_id)


async def test_intra_state_split_of_float_problematic_amount_has_no_precision_drift():
    """33.33 split in half is the classic float-drift trap: 33.33 / 2 ==
    16.665 in binary floating point is itself not exact (float(33.33) is
    already not exactly 33.33), and naively splitting + rounding each half
    independently in float space can produce halves that don't reconcile
    back to the original total, or come back with trailing noise digits
    (e.g. 16.664999999999999) instead of a clean 2-decimal-place value.

    This asserts the full path -- schema validation (Decimal, see
    schemas/universal_invoices.py) -> split_tax_amount's Decimal
    arithmetic (app/services/gst_compliance.py) -> the JSON response ->
    what's actually stored in the database -- produces exact, reconciling
    2-decimal-place Decimals with zero float drift anywhere along it."""
    tenant_id = await _make_tenant(state_code="27")
    customer_id = await _make_customer(tenant_id, state_code="27")
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        async with db_session() as db:
            result = await create_invoice_with_stock_deduction(
                db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, tax_amount=33.33),
                str(uuid.uuid4()),
            )

        total_cgst = Decimal(result["total_cgst"])
        total_sgst = Decimal(result["total_sgst"])
        # An odd-paisa total splits unevenly (CGST absorbs the rounded-up
        # half via ROUND_HALF_UP, SGST gets the exact remainder -- see
        # split_tax_amount's own docstring) -- both land exactly on 2
        # decimal places, and reconcile to precisely the original amount,
        # not something like Decimal("16.664999999999999") a naive
        # float-based split (33.33 / 2 in float) could produce.
        assert total_cgst == Decimal("16.67")
        assert total_sgst == Decimal("16.66")
        assert total_cgst + total_sgst == Decimal("33.33")
        assert Decimal(result["total_igst"]) == Decimal("0.00")

        async with db_session() as verify_db:
            item_row = (await verify_db.execute(
                select(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.invoice_id == uuid.UUID(result["id"]))
            )).scalar_one()
            # Read straight off the ORM (a real asyncpg-driven Decimal, no
            # JSON string round-trip involved at all) -- confirms the
            # exactness is real, not an artifact of how the response
            # happens to serialize.
            assert item_row.cgst_amount == Decimal("16.67")
            assert item_row.sgst_amount == Decimal("16.66")
            assert item_row.cgst_amount + item_row.sgst_amount == Decimal("33.33")
    finally:
        await _cleanup(tenant_id)


async def test_invoice_numbers_gapless_and_unique_sequential_creation():
    """Ten back-to-back invoices (same tenant, same financial year) must
    receive exactly ten unique, contiguous sequence numbers -- no gaps, no
    duplicates."""
    tenant_id = await _make_tenant(state_code="27")
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 100)
    try:
        numbers = []
        for _ in range(10):
            customer_id = await _make_customer(tenant_id, state_code="27")
            async with db_session() as db:
                result = await create_invoice_with_stock_deduction(
                    db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, quantity=1),
                    str(uuid.uuid4()),
                )
            numbers.append(result["invoice_number"])

        assert len(numbers) == len(set(numbers)), f"duplicate invoice numbers: {numbers}"
        sequence_numbers = sorted(int(n.rsplit("/", 1)[-1]) for n in numbers)
        assert sequence_numbers == list(range(sequence_numbers[0], sequence_numbers[0] + 10)), (
            f"expected a gapless contiguous run, got: {sequence_numbers}"
        )
        for n in numbers:
            assert n.startswith("INV/")
    finally:
        await _cleanup(tenant_id)


async def test_invoice_numbers_gapless_and_unique_under_concurrent_creation():
    """The same guarantee, but under genuine concurrency (separate
    sessions racing via asyncio.gather, like
    test_atomic_invoice_stock.py's concurrency test) -- and with one
    request deliberately made to fail (insufficient stock) to prove a
    rolled-back attempt does not burn a number and leave a gap."""
    tenant_id = await _make_tenant(state_code="27")
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    # Enough stock for exactly 5 of the 6 concurrent attempts below.
    await _seed_stock(tenant_id, item_id, warehouse_id, 5)
    try:
        async def _attempt():
            customer_id = await _make_customer(tenant_id, state_code="27")
            async with db_session() as db:
                return await create_invoice_with_stock_deduction(
                    db, tenant_id, uuid.uuid4(), _payload(customer_id, warehouse_id, item_id, quantity=1),
                    str(uuid.uuid4()),
                )

        results = await asyncio.gather(*[_attempt() for _ in range(6)], return_exceptions=True)
        successes = [r for r in results if not isinstance(r, BaseException)]
        failures = [r for r in results if isinstance(r, BaseException)]

        assert len(successes) == 5, f"expected exactly 5 successes, got {len(successes)}: {results}"
        assert len(failures) == 1

        numbers = [r["invoice_number"] for r in successes]
        assert len(numbers) == len(set(numbers)), f"duplicate invoice numbers: {numbers}"
        sequence_numbers = sorted(int(n.rsplit("/", 1)[-1]) for n in numbers)
        # Gapless: exactly 5 contiguous numbers, even though 6 attempts
        # were made and one was rejected/rolled back.
        assert sequence_numbers == list(range(sequence_numbers[0], sequence_numbers[0] + 5)), (
            f"expected a gapless contiguous run of 5, got: {sequence_numbers}"
        )
    finally:
        await _cleanup(tenant_id)


async def test_concurrent_invoice_numbers_all_succeed_are_unique_and_consecutive():
    """Pure invoice-number concurrency test: N concurrent
    create_invoice_with_stock_deduction calls (via asyncio.gather with
    separate db_session()s) where ALL requests succeed -- enough stock
    is seeded for every attempt.

    Proves that generate_next_number's SELECT ... FOR UPDATE row-lock
    correctly serializes concurrent callers on the same series row so
    that:
      - every generated number is unique (no two sessions mint the same
        sequence value), and
      - the winning sequence numbers form a gapless consecutive run
        (the lock ensures each transaction sees the previous one's
        committed increment before reading the counter).

    This is distinct from the test above, which deliberately induces a
    stock-shortfall failure in one of the concurrent branches.  Here
    there are no failures -- the ONLY thing under test is the numbering
    serialization guarantee.
    """
    _N = 8  # concurrent invoice creations that must all succeed

    tenant_id = await _make_tenant(state_code="27")
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id)
    # Seed exactly enough stock for every concurrent request.
    await _seed_stock(tenant_id, item_id, warehouse_id, float(_N))
    try:
        async def _attempt() -> dict:
            customer_id = await _make_customer(tenant_id, state_code="27")
            async with db_session() as db:
                return await create_invoice_with_stock_deduction(
                    db,
                    tenant_id,
                    uuid.uuid4(),
                    _payload(customer_id, warehouse_id, item_id, quantity=1),
                    str(uuid.uuid4()),
                )

        results = await asyncio.gather(*[_attempt() for _ in range(_N)], return_exceptions=True)

        # All N requests must have succeeded -- any exception here is a
        # test failure, not an acceptable race outcome.
        failures = [r for r in results if isinstance(r, BaseException)]
        assert failures == [], (
            f"expected all {_N} concurrent invoice creations to succeed; "
            f"{len(failures)} failed: {failures}"
        )

        numbers = [r["invoice_number"] for r in results]  # type: ignore[index]

        # 1. Uniqueness: no two concurrent sessions must have minted the
        #    same invoice number.
        assert len(numbers) == len(set(numbers)), (
            f"duplicate invoice numbers under concurrency: {numbers}"
        )

        # 2. Consecutiveness: the sequence part of each number (the
        #    zero-padded suffix after the last "/") must form a gapless
        #    run -- no holes from lost increments, no skips.
        seq_nums = sorted(int(n.rsplit("/", 1)[-1]) for n in numbers)
        expected = list(range(seq_nums[0], seq_nums[0] + _N))
        assert seq_nums == expected, (
            f"invoice sequence numbers are not a gapless consecutive run "
            f"of {_N}: got {seq_nums}, expected {expected}"
        )

        # 3. All numbers carry the correct GST prefix format (INV/<FY>/).
        for n in numbers:
            assert n.startswith("INV/"), f"unexpected invoice number format: {n}"
    finally:
        await _cleanup(tenant_id)
