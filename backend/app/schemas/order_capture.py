"""
app/schemas/order_capture.py
===============================
Request/response shapes for app/services/order_capture.py and
app/api/v1/endpoints/order_capture.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CapturedOrderDraftLineItem(BaseModel):
    """Matches app/models/order_capture.py:CapturedOrderDraft.parsed_line_items'
    JSONB shape exactly -- both the service layer and this schema must stay
    in sync with that model's docstring."""
    raw_text: str
    matched_item_id: uuid.UUID | None = None
    match_confidence: float = Field(..., ge=0.0, le=1.0)
    quantity: float | None = None
    uom: str | None = None
    unit_price: float = 0.0
    needs_review: bool = True
    # True when this line's raw_text matched the coarse prompt-injection
    # keyword filter (app/services/order_capture.py's _contains_suspicious_
    # pattern) -- always paired with needs_review=True and an unmatched/
    # unpriced line (see upload_and_parse). Surfaced to the reviewer UI so
    # a human knows *why* the line needs a closer look, not just that it
    # does.
    flagged_suspicious: bool = False


class CapturedOrderDraftResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID | None
    warehouse_id: uuid.UUID | None
    uploaded_image_ref: str
    parsed_line_items: list[CapturedOrderDraftLineItem]
    status: str
    target_type: str
    resulting_invoice_id: uuid.UUID | None
    resulting_quotation_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DraftImageUrlResponse(BaseModel):
    """A freshly-minted, short-lived signed URL for a draft's uploaded
    photo (see app/services/order_capture.py's get_draft_image_signed_url)
    -- never a stored/public URL. The frontend must request a new one each
    time it wants to display the image (e.g. on mount of the review
    screen), not cache/reuse url past expires_in_seconds."""
    url: str
    expires_in_seconds: int


class UpdateDraftLinesRequest(BaseModel):
    """Replaces parsed_line_items wholesale (matched by array index -- the
    JSONB line items have no stable per-line id of their own) with the
    caller's corrected version. Optionally also corrects customer_id/
    warehouse_id, discovered or changed during review, not just at upload
    time (see order_capture.py's service docstring for why these aren't
    required at upload)."""
    corrected_lines: list[CapturedOrderDraftLineItem]
    customer_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None


class PhotoOriginatedQuotationIdsResponse(BaseModel):
    """Backs the optional "via photo" origin tag on the quotations list
    page -- see app/services/order_capture.py's
    get_photo_originated_quotation_ids."""
    quotation_ids: list[uuid.UUID]


class ConfirmDraftRequest(BaseModel):
    """Optional request body for POST .../confirm -- target_type defaults
    to "invoice", the original behavior, so every existing caller that
    posts no body at all (or an empty one) is completely unaffected. See
    app/services/order_capture.py's confirm_draft for what each value
    does."""
    target_type: Literal["invoice", "quotation"] = "invoice"
