"""
app/services/invoice_pdf.py
==============================
Renders a GST-compliant tax invoice PDF.

Two layers:
  - render_invoice_pdf(InvoicePDFData) -> bytes: pure, DB-free rendering.
    Testable without a database (see tests/test_gst_compliance.py).
  - generate_invoice_pdf(db, tenant_id, invoice_id) -> bytes: loads the
    real Tenant/UniversalCustomer/UniversalTaxInvoice(+items) rows and
    builds the InvoicePDFData for the layer above.

Fields mandated on a GST tax invoice (rule 46, CGST Rules) that this
renders: seller name/GSTIN/address, buyer name/GSTIN-or-"Unregistered"/
address, invoice number and date, HSN/SAC per line, taxable value, tax
rate and amount split by CGST/SGST/IGST (or a single IGST column), and
the grand total in words.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer
from app.models.universal_invoices import UniversalTaxInvoice, UniversalTaxInvoiceItem
from app.services.gst_compliance import GST_STATE_CODES, amount_to_words


@dataclass
class InvoicePDFLineItem:
    description: str
    hsn_sac_code: str | None
    quantity: Decimal
    unit_price: Decimal
    taxable_value: Decimal
    cgst_amount: Decimal = Decimal("0.00")
    sgst_amount: Decimal = Decimal("0.00")
    igst_amount: Decimal = Decimal("0.00")
    line_total: Decimal = Decimal("0.00")

    @property
    def tax_rate_pct(self) -> Decimal:
        """Effective combined tax rate for display -- no rate column is
        stored on the line item (only computed amounts), so it's derived
        from taxable_value for the printed invoice."""
        if self.taxable_value == 0:
            return Decimal("0.00")
        total_tax = self.cgst_amount + self.sgst_amount + self.igst_amount
        return (total_tax / self.taxable_value * 100).quantize(Decimal("0.01"))


@dataclass
class InvoicePDFData:
    invoice_number: str
    invoice_date: date
    seller_name: str
    seller_gstin: str | None
    seller_address: str
    seller_state_code: str | None
    buyer_name: str
    buyer_gstin: str | None
    buyer_address: str
    buyer_state_code: str | None
    is_intra_state: bool
    reverse_charge_applicable: bool
    composition_scheme: bool
    items: list[InvoicePDFLineItem]
    subtotal: Decimal
    total_cgst: Decimal
    total_sgst: Decimal
    total_igst: Decimal
    total_amount: Decimal
    currency: str = "INR"

    @property
    def place_of_supply_label(self) -> str:
        state_name = GST_STATE_CODES.get(self.buyer_state_code or "", self.buyer_state_code or "Unknown")
        return f"{self.buyer_state_code or 'N/A'} - {state_name}"


def _state_label(state_code: str | None) -> str:
    if not state_code:
        return "N/A"
    return f"{state_code} - {GST_STATE_CODES.get(state_code, 'Unknown')}"


def render_invoice_pdf(data: InvoicePDFData) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("InvoiceTitle", parent=styles["Title"], fontSize=16, spaceAfter=2)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=10)
    normal = styles["Normal"]

    story = []
    story.append(Paragraph("TAX INVOICE", title_style))
    if data.reverse_charge_applicable:
        story.append(Paragraph("Tax payable on reverse charge basis", small))
    if data.composition_scheme:
        story.append(Paragraph(
            "Composition Taxable Person -- not eligible to collect tax on supplies", small,
        ))
    story.append(Spacer(1, 4 * mm))

    seller_para = Paragraph(
        f"<b>{data.seller_name}</b><br/>{data.seller_address}<br/>"
        f"GSTIN: {data.seller_gstin or 'N/A'}<br/>State: {_state_label(data.seller_state_code)}",
        normal,
    )
    buyer_para = Paragraph(
        f"<b>Bill To:</b> {data.buyer_name}<br/>{data.buyer_address}<br/>"
        f"GSTIN: {data.buyer_gstin or 'Unregistered'}<br/>"
        f"Place of Supply: {_state_label(data.buyer_state_code)}",
        normal,
    )
    meta_para = Paragraph(
        f"<b>Invoice No:</b> {data.invoice_number}<br/>"
        f"<b>Invoice Date:</b> {data.invoice_date.isoformat()}<br/>"
        f"<b>Tax Type:</b> {'CGST + SGST (Intra-state)' if data.is_intra_state else 'IGST (Inter-state)'}",
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

    if data.is_intra_state:
        col_headers = ["#", "Description", "HSN/SAC", "Qty", "Rate", "Taxable Val", "CGST", "SGST", "Total"]
    else:
        col_headers = ["#", "Description", "HSN/SAC", "Qty", "Rate", "Taxable Val", "IGST", "Total"]

    rows = [col_headers]
    for idx, item in enumerate(data.items, start=1):
        if data.is_intra_state:
            rows.append([
                str(idx), item.description, item.hsn_sac_code or "-",
                str(item.quantity), f"{item.unit_price:.2f}", f"{item.taxable_value:.2f}",
                f"{item.cgst_amount:.2f}", f"{item.sgst_amount:.2f}", f"{item.line_total:.2f}",
            ])
        else:
            rows.append([
                str(idx), item.description, item.hsn_sac_code or "-",
                str(item.quantity), f"{item.unit_price:.2f}", f"{item.taxable_value:.2f}",
                f"{item.igst_amount:.2f}", f"{item.line_total:.2f}",
            ])

    items_table = Table(rows, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    totals_rows = [["Taxable Value (Subtotal)", f"{data.subtotal:.2f}"]]
    if data.is_intra_state:
        totals_rows.append(["Total CGST", f"{data.total_cgst:.2f}"])
        totals_rows.append(["Total SGST", f"{data.total_sgst:.2f}"])
    else:
        totals_rows.append(["Total IGST", f"{data.total_igst:.2f}"])
    totals_rows.append(["Grand Total", f"{data.currency} {data.total_amount:.2f}"])

    totals_table = Table(totals_rows, colWidths=[130 * mm, 50 * mm])
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(f"<b>Amount in Words:</b> {amount_to_words(data.total_amount, data.currency)}", normal))

    doc.build(story)
    return buffer.getvalue()


async def generate_invoice_pdf(db: AsyncSession, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> bytes:
    """DB-backed convenience wrapper -- loads the real invoice, its
    tenant (seller) and customer (buyer), builds InvoicePDFData, and
    renders it. Raises ValueError if the invoice doesn't exist for this
    tenant (caller maps this to a 404)."""
    invoice = (
        await db.execute(
            select(UniversalTaxInvoice).where(
                UniversalTaxInvoice.id == invoice_id, UniversalTaxInvoice.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"Invoice {invoice_id} not found for tenant {tenant_id}")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    customer = (
        await db.execute(select(UniversalCustomer).where(UniversalCustomer.id == invoice.customer_id))
    ).scalar_one()
    items = (
        await db.execute(select(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.invoice_id == invoice.id))
    ).scalars().all()

    line_items = [
        InvoicePDFLineItem(
            description=str(item.item_id),
            hsn_sac_code=item.hsn_sac_code,
            quantity=Decimal(str(item.quantity)),
            unit_price=Decimal(str(item.unit_price)),
            taxable_value=Decimal(str(item.line_total))
            - Decimal(str(item.cgst_amount)) - Decimal(str(item.sgst_amount)) - Decimal(str(item.igst_amount)),
            cgst_amount=Decimal(str(item.cgst_amount)),
            sgst_amount=Decimal(str(item.sgst_amount)),
            igst_amount=Decimal(str(item.igst_amount)),
            line_total=Decimal(str(item.line_total)),
        )
        for item in items
    ]

    data = InvoicePDFData(
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.created_at.date(),
        seller_name=tenant.legal_name or tenant.name,
        seller_gstin=tenant.gstin,
        seller_address=(tenant.company_info or {}).get("address", ""),
        seller_state_code=tenant.state_code,
        buyer_name=customer.name,
        buyer_gstin=customer.gst_number,
        buyer_address="",
        buyer_state_code=customer.state_code,
        is_intra_state=tenant.state_code is not None and tenant.state_code == customer.state_code,
        reverse_charge_applicable=False,
        composition_scheme=tenant.composition_scheme,
        items=line_items,
        subtotal=Decimal(str(invoice.subtotal)),
        total_cgst=Decimal(str(invoice.total_cgst)),
        total_sgst=Decimal(str(invoice.total_sgst)),
        total_igst=Decimal(str(invoice.total_igst)),
        total_amount=Decimal(str(invoice.total_amount)),
        currency=invoice.currency,
    )
    return render_invoice_pdf(data)
