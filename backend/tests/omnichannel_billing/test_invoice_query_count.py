"""
tests/omnichannel_billing/test_invoice_query_count.py
=====================================================
Regression test: fetching a page of N invoices (each with M items) must
issue a *constant* number of database round-trips regardless of N.  The
acceptable maximum is:

  1  -- SELECT COUNT(*) for pagination metadata
  1  -- SELECT * FROM universal_tax_invoices WHERE tenant_id = ...
  1  -- SELECT * FROM universal_tax_invoice_items WHERE invoice_id IN (...)
  ─────
  ≤ 3  total queries for any page size

If eager loading were missing (i.e. the items relationship were still
lazy), serializing the response would trigger an additional SELECT per
invoice row, giving 1 + 1 + N queries -- a classic N+1.

Query counting technique
------------------------
SQLAlchemy exposes a synchronous ``before_cursor_execute`` event on the
underlying sync engine.  We attach a counter listener inside the test,
execute the list endpoint call, then detach the listener.  This is the
standard, library-idiomatic way to count round-trips without a proxy or
special driver.

The counter is attached to ``engine.sync_engine`` (not ``engine``) because
``event.listen`` only works with the synchronous Core engine object.
"""
from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from sqlalchemy import event

from app.core.database import engine, db_session
from app.crud import universal_invoices as crud_invoices
from app.models.universal_invoices import UniversalTaxInvoice, UniversalTaxInvoiceItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_tenant(db) -> uuid.UUID:
    """Create a minimal tenant row and return its id."""
    from sqlalchemy import text
    tid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO tenants (id, name, slug, gstin, state_code) "
            "VALUES (:id, :name, :slug, :gstin, :sc) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": tid, "name": f"QC-Tenant-{tid}", "slug": str(tid), "gstin": "27AAPFU0939F1ZV", "sc": "27"},
    )
    return tid


async def _create_customer(db, tenant_id: uuid.UUID) -> uuid.UUID:
    from sqlalchemy import text
    cid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO universal_customers (id, tenant_id, name, currency, status) "
            "VALUES (:id, :tid, :name, 'INR', 'ACTIVE') ON CONFLICT DO NOTHING"
        ),
        {"id": cid, "tid": tenant_id, "name": f"Cust-{cid}"},
    )
    return cid


async def _seed_invoices(
    db, tenant_id: uuid.UUID, customer_id: uuid.UUID,
    *, n_invoices: int = 10, items_per_invoice: int = 3,
) -> None:
    """Insert N invoices, each with M items, in a single flush."""
    from sqlalchemy import text
    item_master_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO universal_item_master "
            "(id, tenant_id, item_code, sku, name, status, is_active, images, documents, variants, attributes) "
            "VALUES (:id, :tid, :code, :sku, :name, 'active', TRUE, '{}', '{}', '{}', '{}') "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": item_master_id, "tid": tenant_id, "code": f"IC-{item_master_id}", "sku": f"SK-{item_master_id}", "name": "Query-Count Item"},
    )

    for i in range(n_invoices):
        inv_id = uuid.uuid4()
        await db.execute(
            text(
                "INSERT INTO universal_tax_invoices "
                "(id, tenant_id, customer_id, invoice_number, status, currency, "
                "is_tax_inclusive, subtotal, total_cgst, total_sgst, total_igst, "
                "tds_amount, total_amount) "
                "VALUES (:id, :tid, :cid, :inv_no, 'DRAFT', 'INR', FALSE, "
                "100.00, 9.00, 9.00, 0.00, 0.00, 118.00)"
            ),
            {"id": inv_id, "tid": tenant_id, "cid": customer_id, "inv_no": f"QC/TEST/{i+1:05d}"},
        )
        for j in range(items_per_invoice):
            await db.execute(
                text(
                    "INSERT INTO universal_tax_invoice_items "
                    "(id, tenant_id, invoice_id, item_id, quantity, unit_price, "
                    "cgst_amount, sgst_amount, igst_amount, line_total) "
                    "VALUES (:id, :tid, :inv_id, :item_id, 1, 100.00, "
                    "9.00, 9.00, 0.00, 118.00)"
                ),
                {"id": uuid.uuid4(), "tid": tenant_id, "inv_id": inv_id, "item_id": item_master_id},
            )


async def _cleanup(db, tenant_id: uuid.UUID) -> None:
    from sqlalchemy import text
    await db.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant_id})


# ---------------------------------------------------------------------------
# Query counter fixture
# ---------------------------------------------------------------------------

class _QueryCounter:
    """Counts the number of SQL statements executed on a sync engine."""

    def __init__(self):
        self.count = 0

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_invoices_query_count_is_constant():
    """Fetching a list of 10 invoices (each with 3 items) must issue ≤ 3
    total SQL queries, proving that selectinload eliminates N+1 reads.

    Query budget:
      query 1  -- SELECT COUNT(*) from universal_tax_invoices (pagination)
      query 2  -- SELECT * FROM universal_tax_invoices WHERE tenant_id=...
      query 3  -- SELECT * FROM universal_tax_invoice_items WHERE invoice_id IN (...)
    """
    N_INVOICES = 10
    ITEMS_PER_INVOICE = 3
    MAX_QUERIES = 3  # count + invoices + items (selectinload IN-batch)

    async with db_session() as db:
        tenant_id = await _create_tenant(db)
        customer_id = await _create_customer(db, tenant_id)
        await _seed_invoices(db, tenant_id, customer_id, n_invoices=N_INVOICES, items_per_invoice=ITEMS_PER_INVOICE)

    try:
        async with db_session() as db:
            counter = _QueryCounter()
            event.listen(engine.sync_engine, "before_cursor_execute", counter)
            try:
                invoices, total = await crud_invoices.list_tax_invoices(
                    db, tenant_id, limit=N_INVOICES, offset=0
                )
            finally:
                event.remove(engine.sync_engine, "before_cursor_execute", counter)

        # Basic correctness checks
        assert total == N_INVOICES, f"expected {N_INVOICES} invoices, got {total}"
        assert len(invoices) == N_INVOICES

        for inv in invoices:
            # items must be populated (not an unloaded lazy proxy)
            assert isinstance(inv.items, list), (
                f"invoice {inv.id}: items is not a list — eager loading broken"
            )
            assert len(inv.items) == ITEMS_PER_INVOICE, (
                f"invoice {inv.id}: expected {ITEMS_PER_INVOICE} items, "
                f"got {len(inv.items)}"
            )

        # N+1 check: total query count must be constant regardless of N_INVOICES
        assert counter.count <= MAX_QUERIES, (
            f"N+1 regression: expected ≤ {MAX_QUERIES} queries for {N_INVOICES} "
            f"invoices, but {counter.count} were issued. "
            f"selectinload(UniversalTaxInvoice.items) may be missing from "
            f"crud_invoices.list_tax_invoices()."
        )
    finally:
        async with db_session() as db:
            await _cleanup(db, tenant_id)
