import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter, user_or_ip_key
from app.middleware.rbac import RequirePermission
from app.middleware.tenant_auth import TenantIDDep, UserIDDep
from app.schemas import order_capture as schemas
from app.services import order_capture as service

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]

# Declared Content-Type -> the magic-byte signature that must actually be
# present at the start of the file for that declared type to be trusted.
# A client can lie in the Content-Type header (or send an arbitrary file
# with a spoofed extension) -- this is what actually gets checked before
# the bytes are ever handed to the AI vision provider or Storage.
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAGIC_SNIFF_BYTES = 12  # enough to check the longest signature below (WEBP's RIFF....WEBP)
_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB read chunks, so we never materialize more than one chunk + accumulated bytes at a time before the size cap trips


def _sniff_image_content_type(header: bytes) -> str | None:
    """Real magic-byte sniffing, not the declared Content-Type header --
    returns the actual detected type, or None if the bytes don't match any
    of the three accepted image formats."""
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def _unsupported_media_type_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail={"error": True, "type": "unsupported_media_type", "message": detail},
    )


def _payload_too_large_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail={
            "error": True,
            "type": "file_too_large",
            "message": f"Uploaded file exceeds the {settings.MAX_UPLOAD_BYTES} byte limit.",
        },
    )


@router.post(
    "/upload",
    response_model=schemas.CapturedOrderDraftResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("OrderCapture", "Drafts", "Create"))],
)
@limiter.limit("10/minute", key_func=user_or_ip_key)
async def upload_order_photo(
    request: Request,
    tenant_id: TenantIDDep,
    user_id: UserIDDep,
    db: DBDep,
    file: UploadFile = File(...),
    customer_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
):
    # 1. Declared Content-Type: cheap, no-read rejection of an obviously
    #    wrong upload before touching the body at all.
    if (file.content_type or "") not in _ALLOWED_IMAGE_TYPES:
        raise _unsupported_media_type_error(
            f"Unsupported content type '{file.content_type}'. Only image/jpeg, image/png, and image/webp are accepted."
        )

    # 2. Content-Length pre-check: reject an obviously oversized request
    #    before reading a single byte of the file. Not authoritative on
    #    its own (a client can lie about or omit it) -- the chunked read
    #    below is the real enforcement -- but it turns an oversized
    #    request into an immediate 413 instead of any read at all.
    content_length_header = request.headers.get("content-length")
    if content_length_header is not None:
        try:
            declared_length = int(content_length_header)
        except ValueError:
            declared_length = None
        if declared_length is not None and declared_length > settings.MAX_UPLOAD_BYTES:
            raise _payload_too_large_error()

    # 3. Read in bounded chunks rather than one unbounded file.read() --
    #    aborts as soon as MAX_UPLOAD_BYTES is exceeded, regardless of
    #    what (or whether) Content-Length claimed.
    chunks: list[bytes] = []
    total_bytes = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > settings.MAX_UPLOAD_BYTES:
            raise _payload_too_large_error()
        chunks.append(chunk)
    image_bytes = b"".join(chunks)

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 4. Real magic-byte sniffing -- the declared Content-Type header
    #    (checked in step 1) is caller-supplied and easily spoofed; this
    #    is what actually gates what gets handed to the AI vision
    #    provider and Supabase Storage. The verified type (not the
    #    caller's declared one) is what's passed downstream.
    sniffed_content_type = _sniff_image_content_type(image_bytes[:_MAGIC_SNIFF_BYTES])
    if sniffed_content_type is None:
        raise _unsupported_media_type_error(
            "The uploaded file's contents do not match a supported image format "
            "(image/jpeg, image/png, image/webp), regardless of its declared content type."
        )

    return await service.upload_and_parse(
        db, tenant_id, image_bytes,
        content_type=sniffed_content_type,
        user_id=user_id, customer_id=customer_id, warehouse_id=warehouse_id,
    )


@router.get(
    "/{draft_id}/image-url",
    response_model=schemas.DraftImageUrlResponse,
    dependencies=[Depends(RequirePermission("OrderCapture", "Drafts", "Create"))],
)
async def get_order_capture_image_url(draft_id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    """Returns a fresh, short-lived signed URL for the draft's uploaded
    photo -- the only sanctioned way to view it. The bucket is private
    (enforced at startup, see app/core/storage_security.py), so there is
    no public/stored URL to hand out instead; the frontend must call this
    endpoint whenever it needs to display the image, not cache a URL from
    a previous response past its expiry."""
    url = await service.get_draft_image_signed_url(db, tenant_id, draft_id)
    return schemas.DraftImageUrlResponse(url=url, expires_in_seconds=service.SIGNED_URL_EXPIRY_SECONDS)


@router.get(
    "/photo-originated-quotation-ids",
    response_model=schemas.PhotoOriginatedQuotationIdsResponse,
    dependencies=[Depends(RequirePermission("OrderCapture", "Drafts", "Create"))],
)
async def get_photo_originated_quotation_ids(tenant_id: TenantIDDep, db: DBDep):
    """Backs the optional "via photo" origin tag on the quotations list
    page -- one call for the whole list, not a per-row lookup. Same
    permission tuple as the other read-only endpoint in this router
    (get_order_capture_image_url) -- OrderCapture has no separate "Read"
    permission defined, only "Create"/"Confirm"."""
    ids = await service.get_photo_originated_quotation_ids(db, tenant_id)
    return schemas.PhotoOriginatedQuotationIdsResponse(quotation_ids=ids)


@router.patch(
    "/{draft_id}/lines",
    response_model=schemas.CapturedOrderDraftResponse,
    dependencies=[Depends(RequirePermission("OrderCapture", "Drafts", "Create"))],
)
async def update_order_capture_lines(
    draft_id: uuid.UUID,
    payload: schemas.UpdateDraftLinesRequest,
    tenant_id: TenantIDDep,
    db: DBDep,
):
    return await service.update_draft_lines(
        db, tenant_id, draft_id,
        [line.model_dump(mode="json") for line in payload.corrected_lines],
        customer_id=payload.customer_id, warehouse_id=payload.warehouse_id,
    )


@router.post(
    "/{draft_id}/confirm",
    dependencies=[Depends(RequirePermission("OrderCapture", "Drafts", "Confirm"))],
)
async def confirm_order_capture_draft(
    draft_id: uuid.UUID,
    tenant_id: TenantIDDep,
    user_id: UserIDDep,
    db: DBDep,
    payload: schemas.ConfirmDraftRequest = schemas.ConfirmDraftRequest(),
    idempotency_key: IdempotencyKeyHeader = None,
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="A verified user is required to confirm an order capture draft.")

    return await service.confirm_draft(
        db, tenant_id, user_id, draft_id, idempotency_key, target_type=payload.target_type,
    )
