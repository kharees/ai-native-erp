"""
app/services/sales_fulfillment.py
====================================
Connects invoice creation to real stock deduction -- previously these were
completely disconnected: crud.universal_invoices.create_tax_invoice never
touched inventory at all, so an invoice could be created for items with
zero stock on hand with nothing anywhere noticing or objecting.

Idempotency + transaction boundary
-----------------------------------
claim_idempotency_key (app/services/idempotency.py) commits its own claim
row immediately -- deliberately, so a concurrent retry with the same key
can see it and get rejected via a real unique-constraint conflict, not a
race (see that module's own docstring). That means it cannot be nested
inside the same `async with db.begin()` block as the invoice+stock work:
calling db.commit() from inside an open db.begin() block breaks that
block's transaction boundary. The structure here is: claim the key first
(its own transaction, already committed by the time this returns) -- then
one atomic db.begin() block for the availability check + invoice creation
+ every line's stock deduction + marking the idempotency key complete --
which all commit together, or all roll back together, when that block
exits. complete_idempotency_key itself only flushes (not commits) for
exactly this reason -- see its own docstring. This matches the exact
pattern app/agent/tools/billing_tools.py's handle_create_invoice/
handle_record_payment already use.

Formerly a known gap (see docs/production-hardening.md's idempotency
entry): if this function rejected the request (insufficient stock ->
HTTPException, or any other exception) after the idempotency key was
already claimed, that claim was left "pending" forever, permanently
409ing every legitimate retry with the same key. Fixed: the entire
`async with db.begin():` block below is wrapped in try/except -- on any
exception, if this call actually won the claim (claim.should_complete),
app.services.idempotency.release_idempotency_key deletes the now-useless
pending row so a retry can claim fresh. This is safe to call after the
`async with db.begin():` block, not inside it: that block's own __aexit__
already rolled back the failed transaction by the time the except clause
runs, leaving the session in a clean state for release's own delete+commit
-- release must never run inside the transaction that's about to roll
back, or it would just roll back too. See release_idempotency_key's own
docstring for the full contract. handle_record_payment and handle_
create_invoice in app/agent/tools/billing_tools.py use the same pattern.

Outbox event: "invoice.created"
-----------------------------------
Written via app.services.outbox.enqueue_event (app/models/outbox.py's
transactional outbox -- see that module's docstring for the full
rationale) in the SAME db.begin() block as the invoice row itself, using
the same `db.add()`-no-commit convention every other outbox call site
uses (app/crud/crud_finance_core.py's approve_journal_voucher is the
only other one). Either both the invoice and the event persist, or
neither does -- there is no window where an invoice exists with no
corresponding event, or vice versa. convert_quotation_to_invoice below
delegates to this same function for its actual invoice creation, so it
gets this event for free -- it does NOT enqueue a second one itself.

Stock-shortfall check: pre-check, not per-line try/rollback
--------------------------------------------------------------
Every line's availability (on-hand minus active, unexpired
StockReservation rows for that item+warehouse -- deliberately NOT the
older, unrelated quantity_reserved/quantity_allocated counters on
UniversalStockBalance, which back the separate, pre-existing reserve_stock/
allocate_stock crud functions this change does not unify with) is checked
BEFORE any write, so a multi-line shortfall can be reported in one
structured error listing every short item, and nothing is written at all
if any line is short (unless the tenant has allow_negative_stock=True).
This leaves a narrow TOCTOU gap under real concurrency -- closed by
execute_stock_movement's own row-level lock (_get_or_create_balance_locked)
during the real write phase: a genuine race still raises there, and still
rolls back the whole invoice (via the same db.begin() block), just without
the same multi-item detail in the error.

Money: Decimal end to end, never float
----------------------------------------
Every monetary field on the GST schemas (unit_price, cgst/sgst/igst
amounts, subtotal, totals -- see app/schemas/universal_invoices.py) is
Decimal, matching the underlying Numeric(15, 2) columns exactly. This
function used to compute the GST split correctly in Decimal
(gst_compliance.split_tax_amount) and then immediately throw that
precision away with float(cgst)/float(total_cgst) before writing it into
the payload dict -- reintroducing the exact float-rounding bug class this
codebase has already been bitten by once in payment/banking code. No
float() call anywhere in this module's money path now, on either side of
this function: Decimal in from the schema (payload.model_dump() already
returns real Decimal objects for Decimal-typed fields), Decimal through
every computation, Decimal out into UniversalTaxInvoiceCreate and then the
ORM (SQLAlchemy's Numeric columns accept Decimal natively -- better than
float, not a conversion).

`quantity` is the one exception, and deliberately not "money" -- it's
still a plain float (Numeric(15, 4) in the DB, but a count of units, not
currency). Multiplying a float quantity against a Decimal money value
raises TypeError directly (Python refuses to guess which side should
convert) rather than silently mixing precision domains -- every such spot
in this module lifts the float into Decimal space explicitly via its
exact string representation first (Decimal(str(x)), never Decimal(x) on
a float, which reads out the underlying binary noise instead of the
decimal digits actually written) before doing arithmetic, and quantizes
back to 2 decimal places (ROUND_HALF_UP, matching gst_compliance.py's own
convention) only once, at the end, when the result needs to land in a
Numeric(15, 2) field.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import universal_invoices as crud_invoices
from app.crud import universal_numbering as crud_numbering
from app.crud import universal_sales as crud_sales
from app.crud import universal_warehousing as crud_warehousing
from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_sales import UniversalSalesQuotationItem
from app.models.universal_warehousing import StockReservation
from app.schemas.sales_fulfillment import QuotationWithStockCheckCreate
from app.schemas.universal_invoices import (
    UniversalTaxInvoiceCreate,
    UniversalTaxInvoiceCreateWithStock,
    UniversalTaxInvoiceResponse,
)
from app.schemas.universal_sales import UniversalSalesQuotationCreate, UniversalSalesQuotationItemCreate
from app.schemas.universal_warehousing import StockMovementRequest
from app.services.gst_compliance import determine_place_of_supply, get_current_financial_year, split_tax_amount
from app.services.idempotency import claim_idempotency_key, complete_idempotency_key, release_idempotency_key
from app.services.outbox import enqueue_event

_GST_INVOICE_ENTITY_TYPE = "invoice"

_INVOICE_STOCK_ENDPOINT = "sales.invoice_with_stock_deduction"


async def _get_available_quantity(
    db: AsyncSession, tenant_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID,
) -> Decimal:
    balance = await crud_warehousing.get_stock_balance(db, tenant_id, item_id, warehouse_id)
    on_hand = Decimal(str(balance["quantity_on_hand"]))

    reserved_stmt = select(func.coalesce(func.sum(StockReservation.quantity), 0)).where(
        StockReservation.tenant_id == tenant_id,
        StockReservation.item_id == item_id,
        StockReservation.warehouse_id == warehouse_id,
        StockReservation.expires_at > datetime.now(timezone.utc),
    )
    reserved = (await db.execute(reserved_stmt)).scalar_one()
    return on_hand - Decimal(str(reserved))


async def create_invoice_with_stock_deduction(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UniversalTaxInvoiceCreateWithStock,
    idempotency_key: str,
    _release_reservation_ids: list[uuid.UUID] | None = None,
) -> dict[str, Any]:
    """
    _release_reservation_ids: internal, used by convert_quotation_to_invoice
    only. Those reservation rows are deleted *inside* this function's own
    db.begin() block (before the availability check, so the released
    quantity immediately counts as available again) rather than by the
    caller beforehand -- releasing them first and then calling this
    function would flush an uncommitted delete that claim_idempotency_key's
    own commit (below) would immediately make permanent, even if the
    invoice creation subsequently failed and this function's own block
    rolled back. Composing them in one atomic unit is the only way both
    "release" and "create" succeed or fail together.
    """
    claim = await claim_idempotency_key(db, tenant_id, _INVOICE_STOCK_ENDPOINT, idempotency_key)
    if claim.replay_response is not None:
        return claim.replay_response
    if claim.conflict:
        raise HTTPException(
            status_code=409,
            detail="An invoice creation with this idempotency key is already in progress.",
        )

    try:
        async with db.begin():
            if _release_reservation_ids:
                release_stmt = select(StockReservation).where(
                    StockReservation.tenant_id == tenant_id,
                    StockReservation.id.in_(_release_reservation_ids),
                )
                for reservation in (await db.execute(release_stmt)).scalars().all():
                    await db.delete(reservation)
                await db.flush()

            tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()

            short_items: list[dict[str, Any]] = []
            for item in payload.items:
                available = await _get_available_quantity(db, tenant_id, item.item_id, payload.warehouse_id)
                if available < Decimal(str(item.quantity)):
                    short_items.append({
                        "item_id": str(item.item_id),
                        "requested": item.quantity,
                        "available": float(available),
                    })

            if short_items and not tenant.allow_negative_stock:
                raise HTTPException(status_code=400, detail={
                    "error": True,
                    "type": "insufficient_stock",
                    "short_items": short_items,
                })

            # --- GST: place of supply, tax split, and invoice numbering ---
            # None of this is caller-editable -- see gst_compliance.py's module
            # docstring. Every value the payload might carry for invoice_number/
            # cgst_amount/sgst_amount/igst_amount is discarded and replaced here.
            customer = (
                await db.execute(select(UniversalCustomer).where(UniversalCustomer.id == payload.customer_id))
            ).scalar_one()

            invoice_dump = payload.model_dump(exclude={"warehouse_id"})

            if tenant.composition_scheme:
                # Composition-scheme dealers don't collect itemized GST from
                # customers on the invoice at all (they pay a flat tax to the
                # government out of their own margin) -- every line's tax split
                # is zeroed, not computed from place of supply.
                for item in invoice_dump["items"]:
                    item["cgst_amount"] = Decimal("0.00")
                    item["sgst_amount"] = Decimal("0.00")
                    item["igst_amount"] = Decimal("0.00")
                invoice_dump["total_cgst"] = Decimal("0.00")
                invoice_dump["total_sgst"] = Decimal("0.00")
                invoice_dump["total_igst"] = Decimal("0.00")
            else:
                place_of_supply = determine_place_of_supply(tenant.state_code, customer.state_code)
                total_cgst = total_sgst = total_igst = Decimal("0.00")
                for item in invoice_dump["items"]:
                    # model_dump() (mode="python", the default) on the now-
                    # Decimal schema fields already returns real Decimal
                    # objects here -- Decimal(str(...)) is still applied
                    # defensively (handles a bare int/str default just as
                    # safely) rather than assumed, but there is no float in
                    # this line at any point, unlike before.
                    line_tax = (
                        Decimal(str(item.get("cgst_amount", 0)))
                        + Decimal(str(item.get("sgst_amount", 0)))
                        + Decimal(str(item.get("igst_amount", 0)))
                    )
                    cgst, sgst, igst = split_tax_amount(line_tax, place_of_supply.is_intra_state)
                    item["cgst_amount"] = cgst
                    item["sgst_amount"] = sgst
                    item["igst_amount"] = igst
                    total_cgst += cgst
                    total_sgst += sgst
                    total_igst += igst
                invoice_dump["total_cgst"] = total_cgst
                invoice_dump["total_sgst"] = total_sgst
                invoice_dump["total_igst"] = total_igst

            # Generated inside this same db.begin() block, not before it: if
            # this transaction rolls back (insufficient stock, a lost stock
            # race, etc.) the sequence increment below rolls back with it, so
            # the number is never burned -- the next successful invoice reuses
            # it instead of leaving a gap. See generate_next_number's docstring.
            invoice_dump["invoice_number"] = await crud_numbering.generate_next_number(
                db, tenant_id, _GST_INVOICE_ENTITY_TYPE, financial_year=get_current_financial_year(),
            )

            invoice_create = UniversalTaxInvoiceCreate(**invoice_dump)
            invoice = await crud_invoices.create_tax_invoice(db, tenant_id, invoice_create)

            await enqueue_event(db, tenant_id, "invoice.created", {
                "invoice_id": str(invoice.id),
                "tenant_id": str(tenant_id),
                "customer_id": str(invoice.customer_id),
                "total_amount": str(invoice.total_amount),
                "invoice_number": invoice.invoice_number,
                "created_at": invoice.created_at.isoformat(),
            })

            for item in payload.items:
                movement = StockMovementRequest(
                    item_id=item.item_id,
                    warehouse_id=payload.warehouse_id,
                    transaction_type="OUT",
                    reference_type="invoice",
                    reference_id=str(invoice.id),
                    quantity=item.quantity,
                )
                try:
                    await crud_warehousing.execute_stock_movement(db, tenant_id, user_id, movement)
                except ValueError as exc:
                    # A genuine race caught at write time despite the pre-check
                    # above (see module docstring) -- still a structured error,
                    # just without the other lines' detail the pre-check gives.
                    raise HTTPException(status_code=400, detail={
                        "error": True,
                        "type": "insufficient_stock",
                        "short_items": [{"item_id": str(item.item_id), "detail": str(exc)}],
                    })

            response_body = UniversalTaxInvoiceResponse.model_validate(invoice).model_dump(mode="json")

            if claim.should_complete:
                await complete_idempotency_key(
                    db, tenant_id, _INVOICE_STOCK_ENDPOINT, idempotency_key, invoice.id, response_body
                )
    except Exception:
        # The `async with db.begin():` block above has already rolled back
        # by the time we get here (its own __aexit__ does that on
        # exception) -- db is in a clean state, safe for release_
        # idempotency_key's own delete+commit. See module docstring and
        # release_idempotency_key's docstring for the full contract.
        if claim.should_complete:
            await release_idempotency_key(db, tenant_id, _INVOICE_STOCK_ENDPOINT, idempotency_key)
        raise

    return response_body


async def create_quotation_with_stock_check(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: QuotationWithStockCheckCreate,
) -> dict[str, Any]:
    """Creates the quotation regardless of current availability (a
    quotation is a soft promise, not a stock-mutating action -- the hard
    block lives in create_invoice_with_stock_deduction, at actual
    fulfillment time) and reserves exactly the requested quantity per line.
    short_items in the response is informational, not an error -- the
    quotation and its reservations are still created."""
    # payload.items' unit_price is Decimal (see schemas/sales_fulfillment.py)
    # but quantity is still float (not money) -- Python can't multiply the
    # two directly, so quantity is lifted into the same Decimal space via
    # its exact string representation (never Decimal(float), which would
    # reintroduce binary float artifacts) for the duration of this sum.
    # UniversalSalesQuotationCreate.total_amount is now Decimal too
    # (Numeric(15, 2) on the DB side) -- no float() round-trip at the
    # boundary anymore; quantized once, here, to the column's 2 decimal
    # places (a sum of Numeric(15,4) quantity * Numeric(15,2) unit_price
    # terms can carry more than 2 decimal places before this).
    total_amount = sum(
        (Decimal(str(item.quantity)) * item.unit_price for item in payload.items),
        start=Decimal("0.00"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    quotation_create = UniversalSalesQuotationCreate(
        customer_id=payload.customer_id,
        quotation_number=payload.quotation_number,
        valid_until=payload.valid_until,
        total_amount=total_amount,
        items=[
            UniversalSalesQuotationItemCreate(item_id=i.item_id, quantity=i.quantity, unit_price=i.unit_price)
            for i in payload.items
        ],
    )
    quotation = await crud_sales.create_quotation(db, tenant_id, quotation_create)

    short_items: list[dict[str, Any]] = []
    for item in payload.items:
        available = await _get_available_quantity(db, tenant_id, item.item_id, payload.warehouse_id)
        if available < Decimal(str(item.quantity)):
            short_items.append({
                "item_id": str(item.item_id),
                "requested": item.quantity,
                "available": float(available),
            })
        reservation = StockReservation(
            tenant_id=tenant_id,
            item_id=item.item_id,
            warehouse_id=payload.warehouse_id,
            quotation_id=quotation.id,
            quantity=Decimal(str(item.quantity)),
            expires_at=payload.reservation_expires_at,
        )
        db.add(reservation)

    await db.flush()
    return {
        "quotation_id": str(quotation.id),
        "quotation_number": quotation.quotation_number,
        "short_items": short_items,
    }


async def convert_quotation_to_invoice(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    quotation_id: uuid.UUID,
    idempotency_key: str,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    quotation = await crud_sales.get_quotation(db, tenant_id, quotation_id)
    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation not found")

    reservations_stmt = select(StockReservation).where(
        StockReservation.tenant_id == tenant_id,
        StockReservation.quotation_id == quotation_id,
    )
    reservations = (await db.execute(reservations_stmt)).scalars().all()
    if not reservations:
        raise HTTPException(status_code=400, detail="Quotation has no active stock reservation to convert.")

    # All reservations for one quotation share the same warehouse_id (set
    # once, at create_quotation_with_stock_check time) -- see module-level
    # design note in sales_fulfillment.py's docstring on why this is
    # derived from the reservation rather than passed in separately.
    warehouse_id = reservations[0].warehouse_id

    items_stmt = select(UniversalSalesQuotationItem).where(
        UniversalSalesQuotationItem.tenant_id == tenant_id,
        UniversalSalesQuotationItem.quotation_id == quotation_id,
    )
    quotation_items = (await db.execute(items_stmt)).scalars().all()

    # invoice_number is intentionally NOT set here -- create_invoice_with_
    # stock_deduction generates it itself, inside its own db.begin() block,
    # so a rolled-back conversion never burns a GST sequence number.
    #
    # quotation.total_amount / qi.unit_price are already Decimal (Numeric
    # columns, read straight off the ORM) -- passed through as-is, not
    # round-tripped via float() as before. qi.quantity stays float
    # (UniversalTaxInvoiceItemBase.quantity is Numeric(15, 4) but
    # deliberately not money -- see schemas/universal_invoices.py), so
    # line_total is computed in Decimal space (exact) and only the final
    # result quantized to the column's 2 decimal places, rather than
    # multiplying two floats and hoping the rounding lands correctly.
    invoice_payload = UniversalTaxInvoiceCreateWithStock(
        customer_id=quotation.customer_id,
        warehouse_id=warehouse_id,
        subtotal=quotation.total_amount,
        total_amount=quotation.total_amount,
        items=[
            {
                "item_id": qi.item_id,
                "quantity": float(qi.quantity),
                "unit_price": qi.unit_price,
                "line_total": (qi.quantity * qi.unit_price).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP,
                ),
            }
            for qi in quotation_items
        ],
    )

    # Reservation release happens *inside* create_invoice_with_stock_
    # deduction's own atomic block (via _release_reservation_ids), not here
    # -- see that function's docstring for why releasing them in this
    # function first would risk permanently losing the reservation if the
    # subsequent invoice creation failed and rolled back.
    response_body = await create_invoice_with_stock_deduction(
        db, tenant_id, user_id, invoice_payload, idempotency_key,
        _release_reservation_ids=[r.id for r in reservations],
    )

    # Marked only after the invoice actually succeeded -- a failed/rolled-
    # back attempt above raises before reaching here, leaving the
    # quotation's status untouched for a legitimate retry. Same status
    # string crud/universal_sales.py's convert_from_quote already uses
    # for its own (separate) quotation-to-order conversion path, kept
    # consistent rather than inventing a second "converted" spelling.
    quotation.status = "CONVERTED"
    await db.flush()

    return response_body
