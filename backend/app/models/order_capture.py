"""
app/models/order_capture.py
==============================
Backs the order-capture pipeline (app/services/order_capture.py): a photo
of a handwritten order -> AI vision extraction -> fuzzy-matched draft line
items -> human review -> a real invoice via app/services/sales_fulfillment.py's
create_invoice_with_stock_deduction.

status lifecycle
-----------------
PARSING     -- upload_and_parse() is running (vision call + item matching).
NEEDS_REVIEW -- at least one line has needs_review=True (low match
                confidence, no resolvable price, or the line's raw_text
                tripped the prompt-injection keyword filter -- see
                app/services/order_capture.py's module docstring).
CONFIRMED   -- every line has needs_review=False (either never flagged, or
               fixed via update_draft_lines()) and confirm_draft() has been
               called successfully.
COMMITTED   -- confirm_draft() completed: either a real invoice was created
               (resulting_invoice_id set, stock deducted immediately) or a
               real quotation was created (resulting_quotation_id set,
               stock only soft-reserved via StockReservation -- see
               target_type below and app/services/sales_fulfillment.py's
               create_quotation_with_stock_check).
REJECTED    -- the draft was discarded without creating an invoice.

target_type
-----------
Which kind of document confirm_draft() should produce -- "invoice"
(default, the original behavior: create_invoice_with_stock_deduction,
real stock deduction) or "quotation" (create_quotation_with_stock_check,
soft stock reservation only). Chosen at confirm time (see
app/schemas/order_capture.py's ConfirmDraftRequest), not at upload time --
recorded here mainly for audit/traceability of which path a given draft
actually took, and so the quotations list can show a "via photo" origin
tag for quotations reachable from a CapturedOrderDraft.
"""

from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
import uuid
from app.core.database import Base

# create_type=False everywhere this is used as a column type -- see
# alembic/versions/*_order_capture.py, which creates the type once via an
# idempotent DO block. Generic sa.Enum's create_type=False is NOT honored
# by Alembic's op.create_table() (a real, previously-diagnosed bug in this
# repo -- see the create_tenant_saree_inventory migration's inventory_status
# column for the same fix); the dialect-specific postgresql.ENUM is.
CapturedOrderDraftStatus = ENUM(
    "PARSING", "NEEDS_REVIEW", "CONFIRMED", "COMMITTED", "REJECTED",
    name="captured_order_draft_status",
    create_type=False,
)


class CapturedOrderDraft(Base):
    __tablename__ = 'captured_order_drafts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_customers.id', ondelete='RESTRICT'), nullable=True, index=True)
    warehouse_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_warehouses.id', ondelete='RESTRICT'), nullable=True)
    uploaded_image_ref = mapped_column(String(512), nullable=False)
    # Raw, unvalidated JSON the vision model returned -- kept verbatim for
    # debugging/audit even after parsed_line_items has been built from it,
    # since parsing/matching logic will change over time and this is the
    # only record of exactly what the model actually said.
    raw_extraction = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"))
    # list[{"raw_text": str, "matched_item_id": str | None,
    #       "match_confidence": float, "quantity": float | None,
    #       "uom": str | None, "unit_price": float, "needs_review": bool,
    #       "flagged_suspicious": bool}]
    # raw_text is truncated to 200 chars and flagged_suspicious/needs_review
    # forced True when it matches a coarse prompt-injection keyword filter
    # -- see app/services/order_capture.py's _contains_suspicious_pattern.
    # The image this is extracted from is untrusted (customer-supplied)
    # input; the system prompt instructs the model to treat all image text
    # as inert data, and this is the independent backstop for when it
    # doesn't (or faithfully transcribes injected text exactly as asked).
    parsed_line_items = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'[]'::jsonb"))
    status = mapped_column(CapturedOrderDraftStatus, nullable=False, server_default=text("'PARSING'"))
    # "invoice" or "quotation" -- see module docstring's "target_type"
    # section. String, not the CapturedOrderDraftStatus-style Postgres
    # ENUM, since this is a small, low-churn set with no need for the
    # ENUM machinery a status column benefits from.
    target_type = mapped_column(String(16), nullable=False, server_default=text("'invoice'"))
    resulting_invoice_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_tax_invoices.id', ondelete='SET NULL'), nullable=True)
    resulting_quotation_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_sales_quotations.id', ondelete='SET NULL'), nullable=True)
    created_by = mapped_column(UUID(as_uuid=True), ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
