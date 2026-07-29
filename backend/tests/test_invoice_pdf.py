"""
tests/test_invoice_pdf.py
============================
Smoke test for app/services/invoice_pdf.py's pure render_invoice_pdf --
confirms it actually produces a well-formed PDF from GST-shaped data
(no database involved; generate_invoice_pdf's DB-loading wrapper is
exercised indirectly wherever real invoices already exist in other
tests).
"""
from datetime import date
from decimal import Decimal

from app.services.invoice_pdf import InvoicePDFData, InvoicePDFLineItem, render_invoice_pdf


def _sample_data(is_intra_state: bool = True) -> InvoicePDFData:
    return InvoicePDFData(
        invoice_number="INV/26-27/00001",
        invoice_date=date(2026, 7, 19),
        seller_name="GST Test Seller Pvt Ltd",
        seller_gstin="27AAAAA0000A1Z5",
        seller_address="123 Seller Street, Mumbai",
        seller_state_code="27",
        buyer_name="Buyer Co",
        buyer_gstin="27BBBBB0000B1Z5" if is_intra_state else "29BBBBB0000B1Z5",
        buyer_address="456 Buyer Road, Mumbai" if is_intra_state else "456 Buyer Road, Bengaluru",
        buyer_state_code="27" if is_intra_state else "29",
        is_intra_state=is_intra_state,
        reverse_charge_applicable=False,
        composition_scheme=False,
        items=[
            InvoicePDFLineItem(
                description="Widget",
                hsn_sac_code="998311",
                quantity=Decimal("2"),
                unit_price=Decimal("100.00"),
                taxable_value=Decimal("200.00"),
                cgst_amount=Decimal("9.00") if is_intra_state else Decimal("0.00"),
                sgst_amount=Decimal("9.00") if is_intra_state else Decimal("0.00"),
                igst_amount=Decimal("0.00") if is_intra_state else Decimal("18.00"),
                line_total=Decimal("218.00"),
            )
        ],
        subtotal=Decimal("200.00"),
        total_cgst=Decimal("9.00") if is_intra_state else Decimal("0.00"),
        total_sgst=Decimal("9.00") if is_intra_state else Decimal("0.00"),
        total_igst=Decimal("0.00") if is_intra_state else Decimal("18.00"),
        total_amount=Decimal("218.00"),
    )


def test_render_invoice_pdf_produces_a_real_pdf_intra_state():
    pdf_bytes = render_invoice_pdf(_sample_data(is_intra_state=True))
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


def test_render_invoice_pdf_produces_a_real_pdf_inter_state():
    pdf_bytes = render_invoice_pdf(_sample_data(is_intra_state=False))
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


def test_render_invoice_pdf_composition_scheme_flag_does_not_crash():
    data = _sample_data(is_intra_state=True)
    data.composition_scheme = True
    data.total_cgst = data.total_sgst = data.total_igst = Decimal("0.00")
    for item in data.items:
        item.cgst_amount = item.sgst_amount = item.igst_amount = Decimal("0.00")
    pdf_bytes = render_invoice_pdf(data)
    assert pdf_bytes.startswith(b"%PDF-")
