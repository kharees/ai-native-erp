"""
app/api/v1/inventory.py
========================
FastAPI router — Inventory Management micro-service endpoints.

Mount point (wired in app/api/v1/router.py → main.py):
    app.include_router(inventory_router,
                       prefix="/api/v1/inventory",
                       tags=["Inventory"])

Endpoint surface
----------------
    GET    /api/v1/inventory                        Paginated list + filters
    POST   /api/v1/inventory                        Create item  → 201
    GET    /api/v1/inventory/stats                  Dashboard aggregate counts
    GET    /api/v1/inventory/{item_id}              Fetch single item
    PATCH  /api/v1/inventory/{item_id}              Partial field update
    PATCH  /api/v1/inventory/{item_id}/attributes   JSONB merge-patch
    DELETE /api/v1/inventory/{item_id}              Soft delete  → 204

Auth model (sprint 1 placeholder)
----------------------------------
    All routes read ``X-Tenant-ID`` and ``X-User-ID`` from HTTP headers.
    These will be replaced by JWT-decoded Supabase session claims once
    the auth middleware is wired in the next sprint.

HTTP error surface
------------------
    400  Bad Request       — invalid UUID header, price-range conflict
    404  Not Found         — item absent from tenant scope
    409  Conflict          — duplicate (tenant_id, sku) on create / rename
    422  Unprocessable     — Pydantic validation failure (FastAPI automatic)
    500  Internal Error    — unhandled exception → global handler in main.py
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud import inventory as crud
from app.schemas.inventory import (
    AttributesPatchPayload,
    InventoryFilterParams,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventoryListResponse,
)

log = structlog.get_logger(__name__)
router = APIRouter()


# =============================================================================
# Typed response model for /stats
# =============================================================================

class InventoryStatsResponse(BaseModel):
    """Aggregate inventory counts returned by GET /stats."""
    total:     int = Field(..., ge=0, description="All active items for this tenant")
    active:    int = Field(..., ge=0, description="Items with status='active'")
    draft:     int = Field(..., ge=0, description="Items with status='draft'")
    low_stock: int = Field(..., ge=0,
                            description="Items where quantity_on_hand ≤ reorder_level")


# =============================================================================
# Dependency helpers
# =============================================================================

async def _resolve_tenant_id(
    x_tenant_id: Annotated[
        str,
        Header(
            alias="X-Tenant-ID",
            description=(
                "UUID of the calling user's tenant. "
                "Will be sourced from the decoded Supabase JWT in production."
            ),
        ),
    ],
) -> uuid.UUID:
    """
    Parse and validate the ``X-Tenant-ID`` header as a UUID.

    Raises ``HTTP 400`` if the value is not a valid UUID v4 string.
    In production this dependency will be replaced by a JWT-decoding
    function that extracts ``tenant_id`` from the Supabase session token.
    """
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header must be a valid UUID (e.g. 550e8400-e29b-41d4-a716-446655440000).",
        )


async def _resolve_user_id(
    x_user_id: Annotated[
        str | None,
        Header(
            alias="X-User-ID",
            description=(
                "UUID of the acting user. Optional; written to audit columns "
                "(created_by / updated_by) when provided."
            ),
        ),
    ] = None,
) -> uuid.UUID | None:
    """
    Parse and validate the optional ``X-User-ID`` header.

    Returns ``None`` when the header is absent (anonymous / system call).
    Raises ``HTTP 400`` when the header is present but not a valid UUID.
    """
    if x_user_id is None:
        return None
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-ID header must be a valid UUID when provided.",
        )


# ── Dependency type aliases (for concise route signatures) ───────────────────
TenantDep   = Annotated[uuid.UUID,        Depends(_resolve_tenant_id)]
UserDep     = Annotated[uuid.UUID | None, Depends(_resolve_user_id)]
DBDep       = Annotated[AsyncSession,     Depends(get_db)]


# =============================================================================
# Utility
# =============================================================================

def _not_found(item_id: uuid.UUID) -> HTTPException:
    """Return a consistent 404 HTTPException for missing inventory items."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(
            f"Inventory item '{item_id}' was not found "
            "or does not belong to your tenant."
        ),
    )


# =============================================================================
# GET /stats
# Declared BEFORE /{item_id} to prevent FastAPI route-shadowing.
# =============================================================================

@router.get(
    "/stats",
    response_model=InventoryStatsResponse,
    summary="Aggregate inventory counts for the dashboard stat strip",
    description=(
        "Executes a single SQL query with conditional COUNTs. "
        "Returns total, active, draft, and low-stock item counts "
        "scoped to the calling tenant."
    ),
    operation_id="get_inventory_stats",
)
async def get_stats(
    tenant_id: TenantDep,
    db: DBDep,
) -> InventoryStatsResponse:
    """
    **GET /api/v1/inventory/stats**

    Scoped to the calling tenant via the ``X-Tenant-ID`` header.
    No pagination or filters — returns a single aggregate object.

    Used by the Next.js inventory page to populate the four stat cards
    (Total SKUs / Active / Draft / Low Stock).
    """
    raw: dict[str, int] = await crud.get_inventory_stats(db, tenant_id=tenant_id)
    log.info("api.inventory.stats", tenant_id=str(tenant_id), **raw)
    return InventoryStatsResponse(**raw)


# =============================================================================
# GET /   — paginated list with filters
# =============================================================================

@router.get(
    "",
    response_model=InventoryListResponse,
    summary="List inventory items — paginated, with optional filters",
    operation_id="list_inventory_items",
)
async def list_items(
    tenant_id: TenantDep,
    db: DBDep,
    # ── Query-parameter filters ───────────────────────────────────────────────
    template: Annotated[
        str | None,
        Query(
            description=(
                'Industry template discriminant. '
                'One of: "Manufacturing" | "Retail" | "Services"'
            ),
        ),
    ] = None,
    item_status: Annotated[
        str | None,
        Query(
            alias="status",
            description=(
                'Item lifecycle status. '
                'One of: "active" | "inactive" | "draft" | '
                '"discontinued" | "pending_review"'
            ),
        ),
    ] = None,
    category: Annotated[
        str | None,
        Query(description="Category name — case-insensitive exact match."),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "Trigram full-text search across item name, SKU, and description. "
                "Uses ILIKE pattern matching (Postgres pg_trgm not required for ILIKE)."
            ),
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Query(
            description=(
                "Tag containment filter. Supply multiple times for AND semantics. "
                "Example: ?tags=perishable&tags=cold-chain"
            ),
        ),
    ] = None,
    min_price: Annotated[
        float | None,
        Query(ge=0, description="Minimum unit_price filter (inclusive)."),
    ] = None,
    max_price: Annotated[
        float | None,
        Query(ge=0, description="Maximum unit_price filter (inclusive)."),
    ] = None,
    low_stock: Annotated[
        bool,
        Query(
            description=(
                "When true, return only items where "
                "quantity_on_hand ≤ reorder_level."
            ),
        ),
    ] = False,
    limit: Annotated[
        int,
        Query(ge=1, le=200, description="Page size (1–200). Default: 20."),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Zero-based page offset. Default: 0."),
    ] = 0,
) -> InventoryListResponse:
    """
    **GET /api/v1/inventory**

    Returns a paginated list of active inventory items for the calling tenant.

    All filter parameters are optional and are combined with AND logic.
    Results are ordered by ``updated_at DESC`` (most recently modified first).

    The ``meta`` block in the response carries ``total``, ``limit``,
    ``offset``, and ``has_more`` for client-side pagination.

    **Errors:**
    - ``400 Bad Request`` — ``min_price > max_price`` (cross-field validation).
    """
    filters = InventoryFilterParams(
        template   = template,
        status     = item_status,
        category   = category,
        search     = search,
        tags       = tags,
        min_price  = min_price,
        max_price  = max_price,
        low_stock  = low_stock,
        limit      = limit,
        offset     = offset,
    )

    result = await crud.list_inventory_items(
        db, tenant_id=tenant_id, filters=filters
    )

    log.info(
        "api.inventory.list",
        tenant_id=str(tenant_id),
        total=result.meta.total,
        returned=len(result.items),
    )
    return result


# =============================================================================
# POST /   — create item
# =============================================================================

@router.post(
    "",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inventory item",
    operation_id="create_inventory_item",
)
async def create_item(
    payload:   InventoryItemCreate,
    tenant_id: TenantDep,
    user_id:   UserDep,
    db:        DBDep,
) -> InventoryItemResponse:
    """
    **POST /api/v1/inventory**

    Create a new inventory item for the calling tenant.

    The ``attributes`` field in the request body is a discriminated union.
    Include a ``template`` key to select the industry schema:

    - ``"Manufacturing"`` — required: ``batch_number``, ``unit_of_measure``,
      ``production_date``
    - ``"Retail"`` — required: ``size``, ``color``
    - ``"Services"`` — required: ``service_type``, ``service_duration_hours``

    All attribute fields for the selected template are validated by Pydantic
    before any database write.

    **Errors:**
    - ``409 Conflict`` — SKU already exists for this tenant.
    - ``422 Unprocessable`` — missing required attributes or failed validation.

    **Returns:** The created item with server-generated ``id`` and timestamps.
    """
    try:
        item = await crud.create_inventory_item(
            db,
            payload     = payload,
            tenant_id   = tenant_id,
            created_by  = user_id,
        )
    except IntegrityError as exc:
        await db.rollback()
        orig = str(getattr(exc, "orig", exc))
        if "uq_inventory_items_tenant_sku" in orig:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"An inventory item with SKU '{payload.sku}' "
                    "already exists for this tenant."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A database integrity constraint was violated. "
                "Check your payload for duplicate or invalid values."
            ),
        )

    log.info(
        "api.inventory.create",
        item_id   = str(item.id),
        sku       = item.sku,
        tenant_id = str(tenant_id),
    )
    return InventoryItemResponse.model_validate(item)


# =============================================================================
# GET /{item_id}   — fetch single item
# =============================================================================

@router.get(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Fetch a single inventory item by UUID",
    operation_id="get_inventory_item",
)
async def get_item(
    item_id:   uuid.UUID,
    tenant_id: TenantDep,
    db:        DBDep,
) -> InventoryItemResponse:
    """
    **GET /api/v1/inventory/{item_id}**

    Returns full item detail including the complete ``attributes`` JSONB object.

    The ``attributes.template`` key tells the frontend which industry schema
    applies so it can render the correct dynamic attribute fields.

    **Errors:**
    - ``404 Not Found`` — item doesn't exist or belongs to a different tenant.
    """
    item = await crud.get_inventory_item(
        db, item_id=item_id, tenant_id=tenant_id
    )
    if item is None:
        raise _not_found(item_id)

    return InventoryItemResponse.model_validate(item)


# =============================================================================
# PATCH /{item_id}   — partial field update
# =============================================================================

@router.patch(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Partially update core item fields (PATCH semantics)",
    operation_id="update_inventory_item",
)
async def update_item(
    item_id:   uuid.UUID,
    payload:   InventoryItemUpdate,
    tenant_id: TenantDep,
    user_id:   UserDep,
    db:        DBDep,
) -> InventoryItemResponse:
    """
    **PATCH /api/v1/inventory/{item_id}**

    Applies a partial update — only fields present in the request body are
    modified.  Omitted fields retain their current database values.

    To update the ``attributes`` column entirely, include the full
    discriminated union object in ``payload.attributes``.  For surgical
    key-level attribute merging without touching other keys, use the
    dedicated ``PATCH /{item_id}/attributes`` endpoint.

    **Errors:**
    - ``404 Not Found`` — item not found or wrong tenant.
    - ``409 Conflict`` — SKU rename collides with an existing item.
    """
    try:
        item = await crud.update_inventory_item(
            db,
            item_id    = item_id,
            tenant_id  = tenant_id,
            payload    = payload,
            updated_by = user_id,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The update violates a uniqueness constraint "
                "(most likely a duplicate SKU for this tenant)."
            ),
        )

    if item is None:
        raise _not_found(item_id)

    log.info(
        "api.inventory.update",
        item_id   = str(item_id),
        tenant_id = str(tenant_id),
    )
    return InventoryItemResponse.model_validate(item)


# =============================================================================
# PATCH /{item_id}/attributes   — JSONB merge-patch
# =============================================================================

@router.patch(
    "/{item_id}/attributes",
    response_model=InventoryItemResponse,
    summary="Merge-patch specific JSONB attribute keys (non-destructive)",
    operation_id="patch_inventory_attributes",
)
async def patch_attributes(
    item_id:   uuid.UUID,
    payload:   AttributesPatchPayload,
    tenant_id: TenantDep,
    user_id:   UserDep,
    db:        DBDep,
) -> InventoryItemResponse:
    """
    **PATCH /api/v1/inventory/{item_id}/attributes**

    Merges ``payload.patch`` into the ``attributes`` JSONB column using
    the Postgres ``||`` operator.  Keys present in the existing JSONB but
    **absent** from the patch are preserved (non-destructive shallow merge).

    This is the correct endpoint when you need to update one or two
    attribute keys (e.g. change ``color`` or ``discount_pct``) without
    rebuilding the entire attribute object.

    **Example request body:**
    ```json
    {
      "patch": {
        "color": "Midnight Blue",
        "discount_pct": 15
      }
    }
    ```

    **Errors:**
    - ``404 Not Found`` — item not found or wrong tenant.
    """
    item = await crud.patch_inventory_attributes(
        db,
        item_id    = item_id,
        tenant_id  = tenant_id,
        payload    = payload,
        updated_by = user_id,
    )
    if item is None:
        raise _not_found(item_id)

    log.info(
        "api.inventory.patch_attributes",
        item_id    = str(item_id),
        patch_keys = list(payload.patch.keys()),
        tenant_id  = str(tenant_id),
    )
    return InventoryItemResponse.model_validate(item)


# =============================================================================
# DELETE /{item_id}   — soft delete
# =============================================================================

@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
    summary="Soft-delete an inventory item (sets is_active=False)",
    operation_id="delete_inventory_item",
)
async def delete_item(
    item_id:   uuid.UUID,
    tenant_id: TenantDep,
    user_id:   UserDep,
    db:        DBDep,
) -> None:
    """
    **DELETE /api/v1/inventory/{item_id}**

    Soft-deletes the item by setting ``is_active = False``.

    The record is **preserved** in Postgres for audit, regulatory, and
    traceability purposes.  The item no longer appears in ``GET /inventory``
    list results and ``GET /inventory/{item_id}`` returns ``404``.

    Returns ``204 No Content`` on success (no response body).

    **Errors:**
    - ``404 Not Found`` — item not found or wrong tenant.
    """
    deleted = await crud.delete_inventory_item(
        db,
        item_id    = item_id,
        tenant_id  = tenant_id,
        deleted_by = user_id,
    )
    if not deleted:
        raise _not_found(item_id)

    log.info(
        "api.inventory.delete",
        item_id   = str(item_id),
        tenant_id = str(tenant_id),
    )
    # FastAPI emits an empty 204 body — return None implicitly
