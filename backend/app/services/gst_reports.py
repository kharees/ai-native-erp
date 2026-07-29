"""
app/services/gst_reports.py
==============================
GSTR-1 (invoice-wise outward-supply return) and GSTR-3B (consolidated
monthly summary return) export data, built entirely from GST fields
already computed and stored at invoice-creation time by
app/services/sales_fulfillment.py::create_invoice_with_stock_deduction
(via app/services/gst_compliance.py). This module does NOT recompute
place-of-supply or CGST/SGST/IGST splits -- it only reads and aggregates
what's already on UniversalTaxInvoice / UniversalTaxInvoiceItem.

The app does not file GST returns itself; this produces the same
sections/columns a tenant's CA needs to prepare and file GSTR-1/GSTR-3B
on the government portal (or via offline-tool JSON), not a portal
submission.

GSTR-1 sections (per GSTN's standard invoice-wise return):
  - B2B: every invoice for a customer with a GSTIN (universal_customers.
    gst_number set), invoice-wise.
  - B2CL ("B2C Large"): invoices for a customer WITHOUT a GSTIN, where
    the supply is inter-state AND invoice value > B2C_LARGE_THRESHOLD
    (Rs 2,50,000) -- also invoice-wise, per GSTN's actual B2CL sheet.
  - B2CS ("B2C Small"): every other unregistered-customer invoice --
    aggregated by (place of supply, tax rate), NOT invoice-wise, matching
    GSTN's actual B2CS sheet shape.
  - CDNR / CDNUR: credit and debit notes against registered / unregistered
    customers respectively. KNOWN LIMITATION: UniversalCreditNote/
    UniversalDebitNote (app/models/universal_returns.py) store no CGST/
    SGST/IGST split or HSN code at all -- there is nothing to aggregate
    beyond note number/date/value, so these sections carry value-only
    rows (tax fields are None) rather than fabricating a split. A CA
    would need to fill the tax columns manually until that schema gap is
    closed.
  - HSN: HSN/SAC-wise summary across every invoice line in the period,
    blended tax rate per HSN code.

GSTR-3B totals are built from the exact same invoice query as GSTR-1's
B2B/B2CL/B2CS sections (every invoice falls into exactly one of the
three), so generate_gstr3b_summary's totals reconcile with
generate_gstr1_data's by construction -- summing taxable_value/cgst/sgst/
igst across B2B + B2CL + B2CS always equals the GSTR-3B totals for the
same tenant/period.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_invoices import UniversalTaxInvoice
from app.models.universal_returns import UniversalCreditNote, UniversalDebitNote
from app.services.gst_compliance import GST_STATE_CODES, determine_place_of_supply

# GSTN's fixed B2C-Large threshold: an unregistered, inter-state invoice
# above this value is reported invoice-wise (B2CL) instead of being
# folded into the (place of supply, rate)-aggregated B2CS sheet. Not
# configurable -- it's a statutory figure, not a business setting.
B2C_LARGE_THRESHOLD = Decimal("250000")

_TWO_PLACES = Decimal("0.01")


def _q(value: Decimal | None) -> Decimal:
    return Decimal(value or 0).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _place_of_supply_label(state_code: str | None) -> str:
    if not state_code:
        return "Unknown"
    name = GST_STATE_CODES.get(state_code, "Other Territory")
    return f"{state_code}-{name}"


def resolve_period(financial_year: str, month: int) -> tuple[date, date]:
    """Indian FY "24-25" + calendar month (1-12) -> [period_start, period_end)
    half-open date range. Apr-Dec fall in the FY's start year; Jan-Mar fall
    in the FY's end year (FY "24-25" runs 1 Apr 2024 - 31 Mar 2025)."""
    if month < 1 or month > 12:
        raise ValueError(f"month must be 1-12, got {month}")
    try:
        start_year = 2000 + int(financial_year.split("-")[0])
    except (ValueError, IndexError):
        raise ValueError(f"financial_year must look like '24-25', got {financial_year!r}")
    calendar_year = start_year if month >= 4 else start_year + 1
    period_start = date(calendar_year, month, 1)
    if month == 12:
        period_end = date(calendar_year + 1, 1, 1)
    else:
        period_end = date(calendar_year, month + 1, 1)
    return period_start, period_end


def _blended_rate(taxable_value: Decimal, tax_total: Decimal) -> Decimal:
    if taxable_value == 0:
        return Decimal("0.00")
    return (tax_total / taxable_value * 100).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


async def _load_period_invoices(
    db: AsyncSession, tenant_id: uuid.UUID, period_start: date, period_end: date
) -> list[UniversalTaxInvoice]:
    result = await db.execute(
        select(UniversalTaxInvoice)
        .options(selectinload(UniversalTaxInvoice.items))
        .where(
            UniversalTaxInvoice.tenant_id == tenant_id,
            UniversalTaxInvoice.status != "CANCELLED",
            UniversalTaxInvoice.created_at >= datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc),
            UniversalTaxInvoice.created_at < datetime.combine(period_end, datetime.min.time(), tzinfo=timezone.utc),
        )
        .order_by(UniversalTaxInvoice.created_at)
    )
    return list(result.scalars().unique().all())


async def generate_gstr1_data(
    db: AsyncSession, tenant_id: uuid.UUID, financial_year: str, month: int
) -> dict[str, Any]:
    period_start, period_end = resolve_period(financial_year, month)

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    invoices = await _load_period_invoices(db, tenant_id, period_start, period_end)

    customer_ids = {inv.customer_id for inv in invoices}
    customers: dict[uuid.UUID, UniversalCustomer] = {}
    if customer_ids:
        rows = (await db.execute(
            select(UniversalCustomer).where(UniversalCustomer.id.in_(customer_ids))
        )).scalars().all()
        customers = {c.id: c for c in rows}

    b2b: list[dict[str, Any]] = []
    b2cl: list[dict[str, Any]] = []
    b2cs_buckets: dict[tuple[str, Decimal], dict[str, Any]] = {}
    hsn_buckets: dict[str, dict[str, Any]] = {}

    for inv in invoices:
        customer = customers.get(inv.customer_id)
        buyer_state_code = customer.state_code if customer else None
        pos = determine_place_of_supply(tenant.state_code, buyer_state_code)
        place_of_supply = _place_of_supply_label(pos.buyer_state_code)

        taxable_value = _q(inv.subtotal)
        cgst, sgst, igst = _q(inv.total_cgst), _q(inv.total_sgst), _q(inv.total_igst)
        tax_total = cgst + sgst + igst
        rate = _blended_rate(taxable_value, tax_total)

        row = {
            "gstin": customer.gst_number if customer else None,
            "receiver_name": customer.name if customer else None,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.created_at.date().isoformat(),
            "invoice_value": float(_q(inv.total_amount)),
            "place_of_supply": place_of_supply,
            "reverse_charge": "N",
            "taxable_value": float(taxable_value),
            "tax_rate": float(rate),
            "igst_amount": float(igst),
            "cgst_amount": float(cgst),
            "sgst_amount": float(sgst),
        }

        is_registered = bool(customer and customer.gst_number)
        if is_registered:
            b2b.append(row)
        elif not pos.is_intra_state and taxable_value > B2C_LARGE_THRESHOLD:
            b2cl.append(row)
        else:
            key = (place_of_supply, rate)
            bucket = b2cs_buckets.setdefault(key, {
                "place_of_supply": place_of_supply,
                "tax_rate": float(rate),
                "taxable_value": Decimal("0.00"),
                "igst_amount": Decimal("0.00"),
                "cgst_amount": Decimal("0.00"),
                "sgst_amount": Decimal("0.00"),
                "invoice_count": 0,
            })
            bucket["taxable_value"] += taxable_value
            bucket["igst_amount"] += igst
            bucket["cgst_amount"] += cgst
            bucket["sgst_amount"] += sgst
            bucket["invoice_count"] += 1

        for item in inv.items:
            hsn = item.hsn_sac_code or "UNSPECIFIED"
            line_taxable = _q(item.quantity * item.unit_price)
            line_cgst, line_sgst, line_igst = _q(item.cgst_amount), _q(item.sgst_amount), _q(item.igst_amount)
            bucket = hsn_buckets.setdefault(hsn, {
                "hsn_sac_code": hsn,
                "total_quantity": Decimal("0"),
                "taxable_value": Decimal("0.00"),
                "igst_amount": Decimal("0.00"),
                "cgst_amount": Decimal("0.00"),
                "sgst_amount": Decimal("0.00"),
            })
            bucket["total_quantity"] += item.quantity
            bucket["taxable_value"] += line_taxable
            bucket["igst_amount"] += line_igst
            bucket["cgst_amount"] += line_cgst
            bucket["sgst_amount"] += line_sgst

    b2cs = [
        {**bucket, "taxable_value": float(bucket["taxable_value"]), "igst_amount": float(bucket["igst_amount"]),
         "cgst_amount": float(bucket["cgst_amount"]), "sgst_amount": float(bucket["sgst_amount"])}
        for bucket in b2cs_buckets.values()
    ]

    hsn_summary = []
    for bucket in hsn_buckets.values():
        tax_total = bucket["igst_amount"] + bucket["cgst_amount"] + bucket["sgst_amount"]
        hsn_summary.append({
            "hsn_sac_code": bucket["hsn_sac_code"],
            "total_quantity": float(bucket["total_quantity"]),
            "taxable_value": float(bucket["taxable_value"]),
            "tax_rate": float(_blended_rate(bucket["taxable_value"], tax_total)),
            "igst_amount": float(bucket["igst_amount"]),
            "cgst_amount": float(bucket["cgst_amount"]),
            "sgst_amount": float(bucket["sgst_amount"]),
            "total_value": float(bucket["taxable_value"] + tax_total),
        })

    cdnr, cdnur = await _generate_note_rows(db, tenant, customers, tenant_id, period_start, period_end)

    return {
        "financial_year": financial_year,
        "month": month,
        "period_start": period_start.isoformat(),
        "period_end_exclusive": period_end.isoformat(),
        "b2b": b2b,
        "b2cl": b2cl,
        "b2cs": b2cs,
        "cdnr": cdnr,
        "cdnur": cdnur,
        "hsn_summary": hsn_summary,
        "exports": [],  # No export/SEZ classification exists in the data model yet.
    }


async def _generate_note_rows(
    db: AsyncSession,
    tenant: Tenant,
    invoice_customers: dict[uuid.UUID, UniversalCustomer],
    tenant_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """CDNR (registered recipient) / CDNUR (unregistered) rows. Credit/debit
    notes (app/models/universal_returns.py) store no CGST/SGST/IGST split or
    HSN -- taxable_value/tax fields are None here rather than fabricated;
    only note_value (the stored, untaxed total_amount) is real."""
    start_dt = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(period_end, datetime.min.time(), tzinfo=timezone.utc)

    credit_notes = (await db.execute(
        select(UniversalCreditNote).where(
            UniversalCreditNote.tenant_id == tenant_id,
            UniversalCreditNote.status != "CANCELLED",
            UniversalCreditNote.created_at >= start_dt,
            UniversalCreditNote.created_at < end_dt,
        )
    )).scalars().all()
    debit_notes = (await db.execute(
        select(UniversalDebitNote).where(
            UniversalDebitNote.tenant_id == tenant_id,
            UniversalDebitNote.status != "CANCELLED",
            UniversalDebitNote.created_at >= start_dt,
            UniversalDebitNote.created_at < end_dt,
        )
    )).scalars().all()

    note_customer_ids = {n.customer_id for n in [*credit_notes, *debit_notes]} - set(invoice_customers)
    if note_customer_ids:
        rows = (await db.execute(
            select(UniversalCustomer).where(UniversalCustomer.id.in_(note_customer_ids))
        )).scalars().all()
        invoice_customers = {**invoice_customers, **{c.id: c for c in rows}}

    invoice_numbers: dict[uuid.UUID, str] = {}
    invoice_ids = {n.tax_invoice_id for n in [*credit_notes, *debit_notes] if n.tax_invoice_id}
    if invoice_ids:
        rows = (await db.execute(
            select(UniversalTaxInvoice).where(UniversalTaxInvoice.id.in_(invoice_ids))
        )).scalars().all()
        invoice_numbers = {inv.id: inv.invoice_number for inv in rows}

    cdnr: list[dict[str, Any]] = []
    cdnur: list[dict[str, Any]] = []

    def _row(note, note_type: str) -> dict[str, Any]:
        customer = invoice_customers.get(note.customer_id)
        buyer_state_code = customer.state_code if customer else None
        pos = determine_place_of_supply(tenant.state_code, buyer_state_code)
        return {
            "gstin": customer.gst_number if customer else None,
            "receiver_name": customer.name if customer else None,
            "note_number": note.note_number,
            "note_date": note.created_at.date().isoformat(),
            "note_type": note_type,
            "original_invoice_number": invoice_numbers.get(note.tax_invoice_id),
            "place_of_supply": _place_of_supply_label(pos.buyer_state_code),
            "note_value": float(_q(note.total_amount)),
            "taxable_value": None,
            "igst_amount": None,
            "cgst_amount": None,
            "sgst_amount": None,
        }

    for note in credit_notes:
        row = _row(note, "Credit Note")
        (cdnr if row["gstin"] else cdnur).append(row)
    for note in debit_notes:
        row = _row(note, "Debit Note")
        (cdnr if row["gstin"] else cdnur).append(row)

    return cdnr, cdnur


async def generate_gstr3b_summary(
    db: AsyncSession, tenant_id: uuid.UUID, financial_year: str, month: int
) -> dict[str, Any]:
    """Consolidated monthly totals -- built from the same invoice query as
    generate_gstr1_data's B2B/B2CL/B2CS sections (every invoice falls into
    exactly one of those three buckets), so this always reconciles exactly
    with the sum of GSTR-1's outward-supply sections for the same period."""
    period_start, period_end = resolve_period(financial_year, month)
    invoices = await _load_period_invoices(db, tenant_id, period_start, period_end)

    total_taxable_value = Decimal("0.00")
    total_cgst = Decimal("0.00")
    total_sgst = Decimal("0.00")
    total_igst = Decimal("0.00")
    total_invoice_value = Decimal("0.00")

    for inv in invoices:
        total_taxable_value += _q(inv.subtotal)
        total_cgst += _q(inv.total_cgst)
        total_sgst += _q(inv.total_sgst)
        total_igst += _q(inv.total_igst)
        total_invoice_value += _q(inv.total_amount)

    total_tax_liability = total_cgst + total_sgst + total_igst

    note_value = Decimal("0.00")
    start_dt = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(period_end, datetime.min.time(), tzinfo=timezone.utc)
    for model in (UniversalCreditNote, UniversalDebitNote):
        rows = (await db.execute(
            select(model).where(
                model.tenant_id == tenant_id,
                model.status != "CANCELLED",
                model.created_at >= start_dt,
                model.created_at < end_dt,
            )
        )).scalars().all()
        for note in rows:
            note_value += _q(note.total_amount)

    return {
        "financial_year": financial_year,
        "month": month,
        "period_start": period_start.isoformat(),
        "period_end_exclusive": period_end.isoformat(),
        "invoice_count": len(invoices),
        "total_taxable_value": float(total_taxable_value),
        "total_cgst": float(total_cgst),
        "total_sgst": float(total_sgst),
        "total_igst": float(total_igst),
        "total_tax_liability": float(total_tax_liability),
        "total_invoice_value": float(total_invoice_value),
        # Informational only -- NOT netted into the totals above, since
        # credit/debit notes have no stored tax split to subtract exactly
        # (see _generate_note_rows). A CA must apply this adjustment manually.
        "credit_debit_notes_value": float(note_value),
    }
