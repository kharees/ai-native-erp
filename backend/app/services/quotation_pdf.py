"""
app/services/quotation_pdf.py
================================
Renders a quotation PDF -- same two-layer structure as
app/services/invoice_pdf.py (render_* is pure/DB-free and directly
testable; generate_* loads the real rows and builds the render layer's
dataclass), deliberately much simpler than the invoice PDF: a quotation
carries no GST tax split at all (UniversalSalesQuotationItem has no
cgst/sgst/igst/hsn_sac_code columns -- see app/models/universal_sales.py),
so there is no tax table to render, no place-of-supply, no reverse-charge/
composition-scheme notes.

The one requirement that matters most here: this must never be mistaken
for a real tax invoice. "QUOTATION -- Not a Tax Invoice" is rendered as
the document's title, not a footnote -- see render_quotation_pdf.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import universal_sales as crud_sales
from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_inventory import UniversalItemMaster

# Falls back to this many days from the quotation's created_at when it has
# no explicit valid_until -- same default confirm_draft's photo-to-
# quotation path uses (app/services/order_capture.py's
# _DEFAULT_QUOTATION_VALIDITY_DAYS), kept as its own constant here since a
# manually-created quotation with no valid_until needs the exact same
# fallback and shouldn't have to import a photo-capture-specific module to
# get it.
DEFAULT_VALIDITY_DAYS = 7


@dataclass
class QuotationPDFLineItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


@dataclass
class QuotationPDFData:
    quotation_number: str
    quotation_date: date
    valid_until: date
    seller_name: str
    seller_gstin: str | None
    seller_address: str
    buyer_name: str
    buyer_gstin: str | None
    items: list[QuotationPDFLineItem]
    subtotal: Decimal
    currency: str = "INR"


def render_quotation_pdf(data: QuotationPDFData) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("QuotationTitle", parent=styles["Title"], fontSize=16, spaceAfter=2)
    disclaimer_style = ParagraphStyle(
        "NotATaxInvoice", parent=styles["Normal"], fontSize=10, textColor=colors.red, spaceAfter=4,
    )
    normal = styles["Normal"]

    story = []
    story.append(Paragraph("QUOTATION", title_style))
    # Deliberately its own prominent, colored line directly under the
    # title -- not a footnote -- so this can never be mistaken for a real
    # tax invoice (see this module's docstring).
    story.append(Paragraph("Not a Tax Invoice", disclaimer_style))
    story.append(Spacer(1, 4 * mm))

    seller_para = Paragraph(
        f"<b>{data.seller_name}</b><br/>{data.seller_address}<br/>"
        f"GSTIN: {data.seller_gstin or 'N/A'}",
        normal,
    )
    buyer_para = Paragraph(
        f"<b>Quoted To:</b> {data.buyer_name}<br/>"
        f"GSTIN: {data.buyer_gstin or 'Unregistered'}",
        normal,
    )
    meta_para = Paragraph(
        f"<b>Quotation No:</b> {data.quotation_number}<br/>"
        f"<b>Date:</b> {data.quotation_date.isoformat()}<br/>"
        f"<b>Valid Until:</b> {data.valid_until.isoformat()}",
        normal,
    )

    header_table = Table([[seller_para, meta_para], [buyer_para, ""]], colWidths=[110 * mm, 70 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    rows = [["#", "Description", "Qty", "Unit Price", "Amount"]]
    for idx, item in enumerate(data.items, start=1):
        rows.append([
            str(idx), item.description, str(item.quantity),
            f"{item.unit_price:.2f}", f"{item.line_total:.2f}",
        ])

    items_table = Table(rows, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    totals_table = Table(
        [["Total", f"{data.currency} {data.subtotal:.2f}"]], colWidths=[130 * mm, 50 * mm],
    )
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.75, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "This is a price quotation, not a demand for payment. Prices and availability "
        "are subject to change after the validity date above.",
        normal,
    ))

    doc.build(story)
    return buffer.getvalue()


async def generate_quotation_pdf(
    db: AsyncSession, tenant_id: uuid.UUID, quotation_id: uuid.UUID, *, default_validity_days: int = DEFAULT_VALIDITY_DAYS,
) -> bytes:
    """DB-backed convenience wrapper -- loads the real quotation (+items),
    its tenant (seller) and customer (buyer), builds QuotationPDFData, and
    renders it. Raises ValueError if the quotation doesn't exist for this
    tenant (caller maps this to a 404) -- same contract as
    invoice_pdf.py's generate_invoice_pdf."""
    quotation = await crud_sales.get_quotation(db, tenant_id, quotation_id)
    if quotation is None:
        raise ValueError(f"Quotation {quotation_id} not found for tenant {tenant_id}")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    customer = (
        await db.execute(select(UniversalCustomer).where(UniversalCustomer.id == quotation.customer_id))
    ).scalar_one()

    item_ids = {item.item_id for item in quotation.items}
    item_names: dict[uuid.UUID, str] = {}
    if item_ids:
        rows = (await db.execute(
            select(UniversalItemMaster.id, UniversalItemMaster.name).where(UniversalItemMaster.id.in_(item_ids))
        )).all()
        item_names = {row.id: row.name for row in rows}

    line_items = [
        QuotationPDFLineItem(
            description=item_names.get(item.item_id, str(item.item_id)),
            quantity=Decimal(str(item.quantity)),
            unit_price=Decimal(str(item.unit_price)),
            line_total=(Decimal(str(item.quantity)) * Decimal(str(item.unit_price))).quantize(Decimal("0.01")),
        )
        for item in quotation.items
    ]

    if quotation.valid_until is not None:
        valid_until = quotation.valid_until.date()
    else:
        valid_until = (quotation.created_at + timedelta(days=default_validity_days)).date()

    data = QuotationPDFData(
        quotation_number=quotation.quotation_number,
        quotation_date=quotation.created_at.date(),
        valid_until=valid_until,
        seller_name=tenant.legal_name or tenant.name,
        seller_gstin=tenant.gstin,
        seller_address=(tenant.company_info or {}).get("address", ""),
        buyer_name=customer.name,
        buyer_gstin=customer.gst_number,
        items=line_items,
        subtotal=Decimal(str(quotation.total_amount)),
    )
    return render_quotation_pdf(data)
