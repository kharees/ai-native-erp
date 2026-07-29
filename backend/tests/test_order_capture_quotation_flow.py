"""
tests/test_order_capture_quotation_flow.py
==============================================
Covers the photo-to-quotation flow added alongside the existing photo-to-
invoice flow in app/services/order_capture.py's confirm_draft (branches
on target_type). Same approach as tests/test_order_capture.py: real
seeded data, get_ai_provider/get_supabase mocked at point of use, real
item matching/pricing/stock-reservation/invoice creation otherwise.

Covers:
  - target_type="quotation" creates a real UniversalSalesQuotation and a
    StockReservation, WITHOUT deducting real stock.
  - that quotation converts to a real invoice via the existing,
    unmodified-for-this-purpose convert_quotation_to_invoice, deducting
    stock only at that point (not before).
  - target_type omitted (the default) still creates an invoice directly,
    exactly as before this feature existed -- the original photo-to-
    invoice flow is unchanged.
  - the quotation PDF (app/services/quotation_pdf.py) renders with all
    required fields and the "Not a Tax Invoice" label, for both a
    photo-originated quotation and a plain render_quotation_pdf() call.
"""
import base64
import json
import re
import uuid
import zlib
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.core.database import db_session
from app.crud import universal_warehousing as crud_warehousing
from app.models.order_capture import CapturedOrderDraft
from app.models.tenants import Tenant
from app.models.universal_customers import UniversalCustomer, UniversalCustomerGroup
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_invoices import UniversalTaxInvoice, UniversalTaxInvoiceItem
from app.models.universal_ledger import UniversalInventoryLedger
from app.models.universal_sales import UniversalCustomerPriceList, UniversalSalesQuotation, UniversalSalesQuotationItem
from app.models.universal_warehousing import StockReservation, UniversalStockBalance, UniversalStockTransaction, UniversalWarehouse
from app.schemas.universal_warehousing import StockMovementRequest
from app.services import order_capture as service
from app.services.quotation_pdf import (
    DEFAULT_VALIDITY_DAYS,
    QuotationPDFData,
    QuotationPDFLineItem,
    generate_quotation_pdf,
    render_quotation_pdf,
)
from app.services.sales_fulfillment import convert_quotation_to_invoice

pytestmark = pytest.mark.asyncio


async def _make_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(
            name="Order Capture Quotation Test", slug=f"oc-quote-{uuid.uuid4().hex[:10]}", plan="enterprise",
            gstin="27AAAAA0000A1Z5", legal_name="Order Capture Quotation Test Pvt Ltd", state_code="27",
        )
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant.id


async def _make_customer_group(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        group = UniversalCustomerGroup(tenant_id=tenant_id, name="Retail")
        db.add(group)
        await db.flush()
        await db.refresh(group)
        return group.id


async def _make_customer(tenant_id: uuid.UUID, group_id: uuid.UUID | None = None) -> uuid.UUID:
    async with db_session() as db:
        customer = UniversalCustomer(
            tenant_id=tenant_id, name="Acme Corp", group_id=group_id, email=f"{uuid.uuid4().hex[:8]}@example.com",
            state_code="27",
        )
        db.add(customer)
        await db.flush()
        await db.refresh(customer)
        return customer.id


async def _make_item(tenant_id: uuid.UUID, name: str, item_code: str | None = None) -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=item_code or f"OCQ-{uuid.uuid4().hex[:8]}",
            sku=f"OCQ-SKU-{uuid.uuid4().hex[:8]}", name=name,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_price(tenant_id: uuid.UUID, group_id: uuid.UUID, item_id: uuid.UUID, price: float) -> None:
    async with db_session() as db:
        db.add(UniversalCustomerPriceList(tenant_id=tenant_id, customer_group_id=group_id, item_id=item_id, price=price))
        await db.flush()


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Order Capture Quotation Test WH", code=f"OCQ-WH-{uuid.uuid4().hex[:8]}")
        db.add(warehouse)
        await db.flush()
        await db.refresh(warehouse)
        return warehouse.id


async def _seed_stock(tenant_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID, quantity: float) -> None:
    async with db_session() as db:
        await crud_warehousing.execute_stock_movement(
            db, tenant_id, None,
            StockMovementRequest(item_id=item_id, warehouse_id=warehouse_id, transaction_type="IN", reference_type="test_seed", quantity=quantity),
        )


async def _on_hand(tenant_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID) -> float:
    async with db_session() as db:
        balance = (await db.execute(
            select(UniversalStockBalance).where(
                UniversalStockBalance.tenant_id == tenant_id,
                UniversalStockBalance.item_id == item_id,
                UniversalStockBalance.warehouse_id == warehouse_id,
            )
        )).scalar_one()
        return float(balance.quantity_on_hand)


def _decode_pdf_text(pdf_bytes: bytes) -> str:
    """reportlab's default output flate-compresses (and Ascii85-encodes on
    top) every content stream -- the actual drawn text ("QUOTATION",
    "Not a Tax Invoice", etc.) is NOT literally present as ASCII in the
    raw PDF bytes, only inside these compressed streams. Extracts every
    `stream ... endstream` block declared with the
    "/Filter [ /ASCII85Decode /FlateDecode ]" reportlab always uses,
    reverses both filters (base64.a85decode then zlib.decompress), and
    concatenates the result -- real PDF content-stream operators (e.g.
    "(QUOTATION) Tj"), not a rendered/laid-out string, but sufficient to
    assert a given literal string was actually drawn somewhere on the
    page. No external PDF-parsing library -- matches tests/
    test_invoice_pdf.py's existing (lighter, non-text-checking) smoke-test
    precedent for this same reportlab setup, just decoded far enough to
    also assert on content, not merely "valid PDF bytes came out"."""
    text_chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.DOTALL):
        raw_stream = match.group(1).strip(b"\r\n")
        try:
            decompressed = zlib.decompress(base64.a85decode(raw_stream, adobe=True))
        except (zlib.error, ValueError):
            continue
        text_chunks.append(decompressed.decode("latin-1", errors="ignore"))
    return "\n".join(text_chunks)


def _mock_vision_response(line_items: list[dict]) -> AsyncMock:
    provider = AsyncMock()
    provider.complete = AsyncMock(return_value=json.dumps({"line_items": line_items}))
    return provider


async def _upload_and_get_confirmable_draft(
    tenant_id: uuid.UUID, customer_id: uuid.UUID, warehouse_id: uuid.UUID, item_id: uuid.UUID,
    *, quantity: float = 2, unit_price: float = 120.0,
) -> CapturedOrderDraft:
    """Uploads a photo whose one line matches item_id exactly (confidence
    1.0) and has a real price, so the draft comes back CONFIRMED and
    ready for confirm_draft() with no manual correction step needed --
    the quotation-branch tests care about confirm_draft's own behavior,
    not re-testing the matching/pricing pipeline test_order_capture.py
    already covers."""
    # _match_line_item's fuzzy path won't hit 1.0 confidence for arbitrary
    # raw_text, so line up the raw_text with the real item's name exactly
    # instead (token_sort_ratio("x","x") == 100).
    async with db_session() as item_db:
        item = (await item_db.execute(select(UniversalItemMaster).where(UniversalItemMaster.id == item_id))).scalar_one()
        item_name = item.name

    vision = _mock_vision_response([{"raw_text": item_name, "quantity": quantity, "unit": "pcs"}])
    with patch("app.services.order_capture.get_ai_provider", return_value=vision), \
         patch("app.services.order_capture.get_supabase") as mock_supabase:
        mock_supabase.return_value.storage.from_.return_value.upload = AsyncMock()
        async with db_session() as db:
            draft = await service.upload_and_parse(
                db, tenant_id, b"fake-image-bytes", customer_id=customer_id, warehouse_id=warehouse_id,
            )
    assert draft.status == "CONFIRMED", f"expected a directly-confirmable draft, got status={draft.status}, lines={draft.parsed_line_items}"
    assert draft.parsed_line_items[0]["unit_price"] == unit_price
    return draft


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(CapturedOrderDraft).where(CapturedOrderDraft.tenant_id == tenant_id))
        await db.execute(delete(StockReservation).where(StockReservation.tenant_id == tenant_id))
        await db.execute(delete(UniversalSalesQuotationItem).where(UniversalSalesQuotationItem.tenant_id == tenant_id))
        await db.execute(delete(UniversalSalesQuotation).where(UniversalSalesQuotation.tenant_id == tenant_id))
        await db.execute(delete(UniversalInventoryLedger).where(UniversalInventoryLedger.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockTransaction).where(UniversalStockTransaction.tenant_id == tenant_id))
        await db.execute(delete(UniversalStockBalance).where(UniversalStockBalance.tenant_id == tenant_id))
        await db.execute(delete(UniversalTaxInvoiceItem).where(UniversalTaxInvoiceItem.tenant_id == tenant_id))
        await db.execute(delete(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomerPriceList).where(UniversalCustomerPriceList.tenant_id == tenant_id))
        await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
        await db.execute(delete(UniversalWarehouse).where(UniversalWarehouse.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomer).where(UniversalCustomer.tenant_id == tenant_id))
        await db.execute(delete(UniversalCustomerGroup).where(UniversalCustomerGroup.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_confirm_as_quotation_reserves_stock_without_deducting_it():
    tenant_id = await _make_tenant()
    group_id = await _make_customer_group(tenant_id)
    customer_id = await _make_customer(tenant_id, group_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id, name="Turmeric Powder 500g", item_code="TUR-500")
    await _make_price(tenant_id, group_id, item_id, 120.0)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        draft = await _upload_and_get_confirmable_draft(tenant_id, customer_id, warehouse_id, item_id)

        user_id = uuid.uuid4()
        async with db_session() as db:
            result = await service.confirm_draft(
                db, tenant_id, user_id, draft.id, str(uuid.uuid4()), target_type="quotation",
            )

        assert "quotation_id" in result
        assert "quotation_number" in result
        assert result["quotation_number"].startswith("QT-CAP-")

        # Stock on hand must be completely untouched -- a quotation only
        # soft-reserves via StockReservation, real deduction only happens
        # at actual invoice time (create_invoice_with_stock_deduction).
        assert await _on_hand(tenant_id, item_id, warehouse_id) == 10.0

        async with db_session() as verify_db:
            reservation = (await verify_db.execute(
                select(StockReservation).where(
                    StockReservation.tenant_id == tenant_id,
                    StockReservation.quotation_id == uuid.UUID(result["quotation_id"]),
                )
            )).scalar_one()
            assert reservation.item_id == item_id
            assert reservation.warehouse_id == warehouse_id
            assert float(reservation.quantity) == 2.0

            quotation = (await verify_db.execute(
                select(UniversalSalesQuotation).where(UniversalSalesQuotation.id == uuid.UUID(result["quotation_id"]))
            )).scalar_one()
            assert quotation.customer_id == customer_id
            assert quotation.total_amount == Decimal("240.00")  # 2 * 120.0

            refreshed_draft = (await verify_db.execute(
                select(CapturedOrderDraft).where(CapturedOrderDraft.id == draft.id)
            )).scalar_one()
            assert refreshed_draft.status == "COMMITTED"
            assert refreshed_draft.target_type == "quotation"
            assert refreshed_draft.resulting_quotation_id == quotation.id
            assert refreshed_draft.resulting_invoice_id is None
    finally:
        await _cleanup(tenant_id)


async def test_photo_originated_quotation_converts_to_invoice_deducting_stock_only_then():
    """The explicit ask: convert_quotation_to_invoice must work completely
    unchanged for a photo-originated quotation, with no idea it came from
    a photo -- same function tests/omnichannel_billing/
    test_atomic_invoice_stock.py already exercises for manually-created
    quotations."""
    tenant_id = await _make_tenant()
    group_id = await _make_customer_group(tenant_id)
    customer_id = await _make_customer(tenant_id, group_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id, name="Turmeric Powder 500g", item_code="TUR-500")
    await _make_price(tenant_id, group_id, item_id, 120.0)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        draft = await _upload_and_get_confirmable_draft(tenant_id, customer_id, warehouse_id, item_id)

        user_id = uuid.uuid4()
        async with db_session() as db:
            quote_result = await service.confirm_draft(
                db, tenant_id, user_id, draft.id, str(uuid.uuid4()), target_type="quotation",
            )
        quotation_id = uuid.UUID(quote_result["quotation_id"])

        # Still untouched immediately after quotation creation.
        assert await _on_hand(tenant_id, item_id, warehouse_id) == 10.0

        async with db_session() as db:
            invoice = await convert_quotation_to_invoice(db, tenant_id, quotation_id, str(uuid.uuid4()), user_id)

        assert invoice["customer_id"] == str(customer_id)
        assert Decimal(invoice["total_amount"]) == Decimal("240.00")

        # Only NOW is real stock deducted.
        assert await _on_hand(tenant_id, item_id, warehouse_id) == 8.0

        async with db_session() as verify_db:
            quotation = (await verify_db.execute(
                select(UniversalSalesQuotation).where(UniversalSalesQuotation.id == quotation_id)
            )).scalar_one()
            assert quotation.status == "CONVERTED"

            # The reservation created at quotation time is released as
            # part of conversion (create_invoice_with_stock_deduction's
            # own _release_reservation_ids), not left dangling.
            remaining_reservations = (await verify_db.execute(
                select(StockReservation).where(StockReservation.quotation_id == quotation_id)
            )).scalars().all()
            assert remaining_reservations == []
    finally:
        await _cleanup(tenant_id)


async def test_confirm_with_default_target_type_still_creates_invoice_directly():
    """target_type omitted entirely -- the original photo-to-invoice flow
    (predating this feature) must behave exactly as before: a real
    invoice, real immediate stock deduction, no quotation/reservation
    created at all."""
    tenant_id = await _make_tenant()
    group_id = await _make_customer_group(tenant_id)
    customer_id = await _make_customer(tenant_id, group_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id, name="Turmeric Powder 500g", item_code="TUR-500")
    await _make_price(tenant_id, group_id, item_id, 120.0)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        draft = await _upload_and_get_confirmable_draft(tenant_id, customer_id, warehouse_id, item_id)

        user_id = uuid.uuid4()
        async with db_session() as db:
            # target_type intentionally not passed -- exercises the
            # keyword-only default, exactly how the pre-existing endpoint
            # callers (posting no body at all) behave.
            invoice = await service.confirm_draft(db, tenant_id, user_id, draft.id, str(uuid.uuid4()))

        assert "id" in invoice
        assert "invoice_number" in invoice
        assert Decimal(invoice["total_amount"]) == Decimal("240.00")
        assert await _on_hand(tenant_id, item_id, warehouse_id) == 8.0  # deducted immediately

        async with db_session() as verify_db:
            no_quotations = (await verify_db.execute(
                select(UniversalSalesQuotation).where(UniversalSalesQuotation.tenant_id == tenant_id)
            )).scalars().all()
            assert no_quotations == []

            refreshed_draft = (await verify_db.execute(
                select(CapturedOrderDraft).where(CapturedOrderDraft.id == draft.id)
            )).scalar_one()
            assert refreshed_draft.target_type == "invoice"
            assert refreshed_draft.resulting_invoice_id is not None
            assert refreshed_draft.resulting_quotation_id is None
    finally:
        await _cleanup(tenant_id)


async def test_confirm_rejects_unknown_target_type():
    tenant_id = await _make_tenant()
    group_id = await _make_customer_group(tenant_id)
    customer_id = await _make_customer(tenant_id, group_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id, name="Turmeric Powder 500g", item_code="TUR-500")
    await _make_price(tenant_id, group_id, item_id, 120.0)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        draft = await _upload_and_get_confirmable_draft(tenant_id, customer_id, warehouse_id, item_id)

        async with db_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await service.confirm_draft(
                    db, tenant_id, uuid.uuid4(), draft.id, str(uuid.uuid4()), target_type="not-a-real-type",
                )
        assert exc_info.value.status_code == 400
    finally:
        await _cleanup(tenant_id)


async def test_quotation_pdf_renders_required_fields_and_not_a_tax_invoice_label():
    tenant_id = await _make_tenant()
    group_id = await _make_customer_group(tenant_id)
    customer_id = await _make_customer(tenant_id, group_id)
    warehouse_id = await _make_warehouse(tenant_id)
    item_id = await _make_item(tenant_id, name="Turmeric Powder 500g", item_code="TUR-500")
    await _make_price(tenant_id, group_id, item_id, 120.0)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    try:
        draft = await _upload_and_get_confirmable_draft(tenant_id, customer_id, warehouse_id, item_id)
        user_id = uuid.uuid4()
        async with db_session() as db:
            quote_result = await service.confirm_draft(
                db, tenant_id, user_id, draft.id, str(uuid.uuid4()), target_type="quotation",
            )
        quotation_id = uuid.UUID(quote_result["quotation_id"])

        async with db_session() as db:
            pdf_bytes = await generate_quotation_pdf(db, tenant_id, quotation_id)

        # A real, non-trivial PDF was produced (%PDF magic bytes; reportlab
        # output for a one-line quotation is comfortably several KB).
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 1000

        # reportlab embeds this as real PDF text objects, not an image --
        # decode the compressed content stream(s) to confirm the required
        # fields were actually drawn, not just that some PDF came out.
        text = _decode_pdf_text(pdf_bytes)
        assert "QUOTATION" in text
        assert "Not a Tax Invoice" in text
        assert quote_result["quotation_number"] in text
    finally:
        await _cleanup(tenant_id)


async def test_render_quotation_pdf_falls_back_to_seven_day_validity_when_unset():
    """render_quotation_pdf itself (the pure, DB-free layer) with an
    explicit QuotationPDFData -- confirms the default-7-days-from-creation
    fallback generate_quotation_pdf applies when a quotation has no
    explicit valid_until, and that the label/seller/buyer fields all
    appear in the rendered output."""
    created = date(2026, 1, 1)
    data = QuotationPDFData(
        quotation_number="QT-TEST-0001",
        quotation_date=created,
        valid_until=created + timedelta(days=DEFAULT_VALIDITY_DAYS),
        seller_name="Test Seller Pvt Ltd",
        seller_gstin="27AAAAA0000A1Z5",
        seller_address="123 Test Street",
        buyer_name="Test Buyer",
        buyer_gstin=None,
        items=[QuotationPDFLineItem(description="Turmeric Powder 500g", quantity=Decimal("2"), unit_price=Decimal("120.00"), line_total=Decimal("240.00"))],
        subtotal=Decimal("240.00"),
    )

    pdf_bytes = render_quotation_pdf(data)
    assert pdf_bytes[:4] == b"%PDF"

    text = _decode_pdf_text(pdf_bytes)
    assert "QUOTATION" in text
    assert "Not a Tax Invoice" in text
    assert "Test Seller Pvt Ltd" in text
    assert "Test Buyer" in text
    assert "QT-TEST-0001" in text
    assert "Unregistered" in text  # buyer_gstin=None renders this, not a blank/crash
    assert (created + timedelta(days=DEFAULT_VALIDITY_DAYS)).isoformat() in text
