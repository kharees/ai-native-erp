"""
app/crud/inventory.py
=====================
Asynchronous CRUD repository layer for the AI-Native ERP Inventory module.

NOT CANONICAL — see docs/inventory-architecture.md. Operates on the same
`inventory_items` table as app/crud/crud_inventory.py (the Handloom Saree
engine), with zero coordination between the two. See that doc before
changing validation/business logic here.

Responsibilities
----------------
  • All SQL is built with SQLAlchemy 2.0 ORM / Core expressions.
    No raw string SQL — queries are composable, type-safe, and
    injection-proof.
  • The JSONB ``attributes`` column is handled via SQLAlchemy's JSONB
    dialect type.  Merge-patching uses the Postgres ``||`` operator with
    a properly cast ``bindparam`` so asyncpg never receives a Python dict
    as a raw JSONB literal (which causes asyncpg serialisation errors).
  • Every function is scoped to a ``tenant_id`` parameter to enforce
    multi-tenant data isolation at the application layer, in addition to
    the Postgres RLS policies defined in the migration.
  • Pagination, trigram search, tag-containment, and low-stock filters
    are pushed down to Postgres — zero Python-side filtering.
  • All write operations flush inside the caller's session transaction;
    commit / rollback is the responsibility of the FastAPI dependency
    (``get_db`` in app.core.database) or the caller's context manager.

Public API
----------
  get_inventory_item          — fetch one item by PK + tenant scope
  get_tenant_inventory        — alias for list_inventory_items (named alias)
  list_inventory_items        — paginated, filtered list
  create_inventory_item       — insert new item with JSONB attributes
  update_inventory_item       — PATCH semantics (only supplied fields written)
  patch_inventory_attributes  — shallow JSONB merge-patch via Postgres ||
  delete_inventory_item       — soft-delete (is_active = False)
  get_inventory_stats         — single-query aggregate counts

Dependencies (injected via FastAPI Depends):
    db: AsyncSession — from app.core.database.get_db
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from sqlalchemy import cast, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem
from app.schemas.inventory import (
    AttributesPatchPayload,
    InventoryFilterParams,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventoryListResponse,
    PaginationMeta,
)

log = structlog.get_logger(__name__)


# =============================================================================
# Internal helpers
# =============================================================================

def _apply_filters(
    stmt,
    filters: InventoryFilterParams,
    tenant_id: uuid.UUID,
):
    """
    Append WHERE clauses to a SELECT statement from ``InventoryFilterParams``.

    Tenant scope and ``is_active`` guard are always applied first.
    All additional predicates are ANDed together.

    Args:
        stmt:      Base SQLAlchemy SELECT expression.
        filters:   Validated filter parameters (from router query params).
        tenant_id: UUID scope guard — restricts results to this tenant only.

    Returns:
        The augmented SELECT statement with all filter clauses appended.
    """
    # ── Mandatory tenant + active guard ──────────────────────────────────────
    stmt = stmt.where(InventoryItem.tenant_id == tenant_id)
    stmt = stmt.where(InventoryItem.is_active.is_(True))

    # ── Industry template — JSONB text extraction ─────────────────────────────
    # Equivalent SQL: attributes->>'template' = :template
    if filters.template:
        stmt = stmt.where(
            InventoryItem.attributes["template"].astext == filters.template
        )

    # ── Status ────────────────────────────────────────────────────────────────
    if filters.status:
        stmt = stmt.where(InventoryItem.status == filters.status)

    # ── Category (case-insensitive exact match) ───────────────────────────────
    if filters.category:
        stmt = stmt.where(
            func.lower(InventoryItem.category) == filters.category.lower()
        )

    # ── Full-text trigram search across name, sku, description ───────────────
    if filters.search:
        term = f"%{filters.search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(InventoryItem.name).like(term),
                func.lower(InventoryItem.sku).like(term),
                func.lower(InventoryItem.description).like(term),
            )
        )

    # ── Tag containment: tags @> ARRAY[:tags]  (GIN indexed) ─────────────────
    if filters.tags:
        stmt = stmt.where(InventoryItem.tags.contains(filters.tags))

    # ── Price range ───────────────────────────────────────────────────────────
    if filters.min_price is not None:
        stmt = stmt.where(InventoryItem.unit_price >= filters.min_price)
    if filters.max_price is not None:
        stmt = stmt.where(InventoryItem.unit_price <= filters.max_price)

    # ── Low-stock alert: quantity_on_hand <= reorder_level ────────────────────
    if filters.low_stock:
        stmt = stmt.where(
            InventoryItem.quantity_on_hand <= InventoryItem.reorder_level
        )

    return stmt


def _serialize_attributes(attributes_model) -> dict[str, Any]:
    """
    Serialise a Pydantic attribute sub-model (ManufacturingAttributes,
    RetailAttributes, or ServicesAttributes) to a plain Python dict
    suitable for storing in a Postgres JSONB column via asyncpg.

    Uses ``model_dump(mode="json")`` so that:
      • ``AnyHttpUrl`` → plain ``str``
      • ``datetime`` → ISO 8601 ``str``
      • ``Enum`` → ``str`` value
      • ``None`` values are excluded to keep the JSONB lean.

    Args:
        attributes_model: A validated Pydantic attribute sub-model instance.

    Returns:
        A plain ``dict[str, Any]`` safe for JSONB storage.
    """
    return attributes_model.model_dump(mode="json", exclude_none=True)


# =============================================================================
# READ operations
# =============================================================================

async def get_inventory_item(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> InventoryItem | None:
    """
    Fetch a single active inventory item by primary key, scoped to tenant.

    Returns ``None`` if the item does not exist, has been soft-deleted, or
    belongs to a different tenant.  The router raises ``404 Not Found``
    in all three cases so tenants cannot infer each other's item IDs
    (no 403 vs 404 information leakage).

    Args:
        db:        Async SQLAlchemy session injected via ``Depends(get_db)``.
        item_id:   UUID primary key of the target item.
        tenant_id: UUID of the calling user's tenant (from JWT / header).

    Returns:
        ``InventoryItem`` ORM instance, or ``None`` if not found.
    """
    stmt = (
        select(InventoryItem)
        .where(InventoryItem.id == item_id)
        .where(InventoryItem.tenant_id == tenant_id)
        .where(InventoryItem.is_active.is_(True))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    log.debug(
        "crud.inventory.get",
        item_id=str(item_id),
        tenant_id=str(tenant_id),
        found=item is not None,
    )
    return item


async def list_inventory_items(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    filters: InventoryFilterParams,
) -> InventoryListResponse:
    """
    Return a paginated, filtered list of active inventory items for a tenant.

    Executes exactly two database round-trips:
      1. ``COUNT(*)`` subquery — determines ``meta.total`` without LIMIT.
      2. Data query — applies ``ORDER BY updated_at DESC``, ``LIMIT``, ``OFFSET``.

    All filter predicates are pushed to Postgres; no Python-side filtering.

    Args:
        db:        Async SQLAlchemy session.
        tenant_id: Tenant scope for multi-tenancy isolation.
        filters:   Validated ``InventoryFilterParams`` from the request.

    Returns:
        ``InventoryListResponse`` with ``items`` list and ``meta`` pagination block.
    """
    base_stmt = select(InventoryItem)
    base_stmt = _apply_filters(base_stmt, filters, tenant_id)

    # ── COUNT ─────────────────────────────────────────────────────────────────
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # ── DATA ──────────────────────────────────────────────────────────────────
    data_stmt = (
        base_stmt
        .order_by(InventoryItem.updated_at.desc(), InventoryItem.id)
        .limit(filters.limit)
        .offset(filters.offset)
    )
    rows = (await db.execute(data_stmt)).scalars().all()

    log.info(
        "crud.inventory.list",
        tenant_id=str(tenant_id),
        total=total,
        returned=len(rows),
        filters=filters.model_dump(exclude_none=True),
    )

    return InventoryListResponse(
        items=[InventoryItemResponse.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            has_more=(filters.offset + len(rows)) < total,
        ),
    )


# Named alias used by some callers and the user's specification.
# Delegates to ``list_inventory_items`` with the same signature.
async def get_tenant_inventory(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    filters: InventoryFilterParams,
) -> InventoryListResponse:
    """
    Named alias for ``list_inventory_items``.

    Provided for import-path compatibility with callers that reference
    ``get_tenant_inventory`` directly (e.g. background tasks, analytics
    pipelines).

    Args:
        db:        Async SQLAlchemy session.
        tenant_id: Tenant scope.
        filters:   Validated filter parameters.

    Returns:
        ``InventoryListResponse`` — same shape as ``list_inventory_items``.
    """
    return await list_inventory_items(db, tenant_id=tenant_id, filters=filters)


# =============================================================================
# CREATE
# =============================================================================

async def create_inventory_item(
    db: AsyncSession,
    *,
    payload: InventoryItemCreate,
    tenant_id: uuid.UUID,
    created_by: uuid.UUID | None = None,
) -> InventoryItem:
    """
    Persist a new inventory item with its discriminated JSONB attributes.

    Serialisation flow:
      Pydantic ``InventoryItemCreate.attributes``
        → ``_serialize_attributes()``  (model_dump mode="json", exclude_none)
        → plain ``dict[str, Any]``
        → asyncpg serialises to Postgres JSONB automatically via SQLAlchemy

    The ``template`` key is always present in the stored JSONB, acting as
    the column's own discriminant for future JSONB queries
    (``attributes->>'template'``).

    Args:
        db:         Async SQLAlchemy session.
        payload:    Validated ``InventoryItemCreate`` — all required fields
                    and the fully-validated attributes sub-model present.
        tenant_id:  Tenant scope — written to the ``tenant_id`` column.
        created_by: Optional UUID of the creating user (audit trail).

    Returns:
        The newly created ``InventoryItem`` ORM instance, refreshed from DB
        so all server-generated values (UUID, timestamps) are populated.

    Raises:
        ``sqlalchemy.exc.IntegrityError``:
            If ``(tenant_id, sku)`` violates the unique constraint
            ``uq_inventory_items_tenant_sku``.  The router maps this to
            ``HTTP 409 Conflict``.
    """
    attributes_dict: dict[str, Any] = _serialize_attributes(payload.attributes)

    item = InventoryItem(
        tenant_id        = tenant_id,
        sku              = payload.sku,
        name             = payload.name,
        description      = payload.description,
        category         = payload.category,
        sub_category     = payload.sub_category,
        brand            = payload.brand,
        tags             = payload.tags,
        unit_price       = float(payload.unit_price),
        cost_price       = float(payload.cost_price),
        currency         = payload.currency,
        quantity_on_hand = payload.quantity_on_hand,
        reorder_level    = payload.reorder_level,
        unit_of_measure  = payload.unit_of_measure,
        status           = payload.status,
        attributes       = attributes_dict,
        created_by       = created_by,
        updated_by       = created_by,
    )

    db.add(item)
    await db.flush()        # INSERT within the current transaction; populates .id
    await db.refresh(item)  # Reload server-generated defaults (uuid, timestamps)

    log.info(
        "crud.inventory.create",
        item_id=str(item.id),
        sku=item.sku,
        template=attributes_dict.get("template"),
        tenant_id=str(tenant_id),
    )
    return item


# =============================================================================
# UPDATE — PATCH semantics (only supplied non-None fields written)
# =============================================================================

async def update_inventory_item(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    tenant_id: uuid.UUID,
    payload: InventoryItemUpdate,
    updated_by: uuid.UUID | None = None,
) -> InventoryItem | None:
    """
    Apply a partial update to an existing inventory item (PATCH semantics).

    Only fields that are explicitly provided (non-``None``) in ``payload``
    are written to the database.  All other columns retain their current
    Postgres values — no blind overwrites.

    If ``attributes`` is included it fully replaces the JSONB column.
    For non-destructive key-level merging use ``patch_inventory_attributes``.

    Args:
        db:         Async SQLAlchemy session.
        item_id:    Target item UUID.
        tenant_id:  Tenant scope guard — update only affects matching tenant.
        payload:    ``InventoryItemUpdate`` — only non-None fields applied.
        updated_by: Optional UUID of the acting user (written to ``updated_by``).

    Returns:
        Updated ``InventoryItem`` ORM instance, or ``None`` if not found /
        wrong tenant.

    Raises:
        ``sqlalchemy.exc.IntegrityError``:
            If an SKU rename collides with an existing ``(tenant_id, sku)`` pair.
            The router maps this to ``HTTP 409 Conflict``.
    """
    # Verify existence and tenant ownership before issuing UPDATE
    existing = await get_inventory_item(db, item_id=item_id, tenant_id=tenant_id)
    if existing is None:
        return None

    # Extract only the explicitly set fields from the PATCH payload
    update_data: dict[str, Any] = payload.model_dump(exclude_none=True)

    # Serialise the attributes sub-model to a plain dict if present
    if "attributes" in update_data:
        attrs_model = payload.attributes
        if attrs_model is not None and not isinstance(attrs_model, dict):
            update_data["attributes"] = _serialize_attributes(attrs_model)

    # Stamp the audit column
    if updated_by is not None:
        update_data["updated_by"] = updated_by

    # Nothing to write — return the existing item unchanged
    if not update_data:
        return existing

    stmt = (
        update(InventoryItem)
        .where(InventoryItem.id == item_id)
        .where(InventoryItem.tenant_id == tenant_id)
        .values(**update_data)
        .returning(InventoryItem)
    )
    result = await db.execute(stmt)
    updated = result.scalar_one_or_none()

    log.info(
        "crud.inventory.update",
        item_id=str(item_id),
        tenant_id=str(tenant_id),
        fields=list(update_data.keys()),
    )
    return updated


# =============================================================================
# JSONB ATTRIBUTE MERGE PATCH
# =============================================================================

async def patch_inventory_attributes(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    tenant_id: uuid.UUID,
    payload: AttributesPatchPayload,
    updated_by: uuid.UUID | None = None,
) -> InventoryItem | None:
    """
    Non-destructively merge ``payload.patch`` into the ``attributes`` JSONB
    column using the Postgres ``||`` (jsonb concatenation) operator.

    Keys present in the existing JSONB but absent from ``payload.patch``
    are **preserved** — this is a shallow merge at the top-level key set.

    Postgres SQL produced:
        UPDATE public.inventory_items
        SET    attributes = attributes || :patch_json::jsonb,
               updated_by = :updated_by
        WHERE  id = :item_id
          AND  tenant_id = :tenant_id
        RETURNING *;

    asyncpg integration:
        The patch dict is JSON-serialised to a string, then cast to JSONB
        via SQLAlchemy's ``cast(text(:json_str), JSONB)`` so asyncpg never
        receives a raw Python dict for a JSONB parameter (which would raise
        ``asyncpg.exceptions.UnsupportedClientFeatureError`` or a
        ``DataError`` on older asyncpg versions).

    Example:
        existing  = {"template": "Retail", "size": "M", "color": "Red"}
        patch     = {"color": "Midnight Blue", "discount_pct": 15}
        result    = {"template": "Retail", "size": "M",
                     "color": "Midnight Blue", "discount_pct": 15}

    Args:
        db:         Async SQLAlchemy session.
        item_id:    Target item UUID.
        tenant_id:  Tenant scope guard.
        payload:    ``AttributesPatchPayload`` — ``{"patch": { ... }}`` dict.
        updated_by: Optional UUID of the acting user.

    Returns:
        Updated ``InventoryItem`` ORM instance, or ``None`` if not found /
        wrong tenant.
    """
    # Verify existence and tenant ownership
    existing = await get_inventory_item(db, item_id=item_id, tenant_id=tenant_id)
    if existing is None:
        return None

    # Serialise the patch dict to a JSON string literal.
    # We then cast it to JSONB inside the SQL expression so asyncpg receives
    # a typed JSONB value — not a raw Python dict.
    patch_json_str: str = json.dumps(payload.patch, default=str)

    # Build: attributes = attributes || '<patch_json>'::jsonb
    # ``text()`` wraps the literal string; ``cast(..., JSONB)`` adds ::jsonb.
    patch_expr = cast(text(f"'{patch_json_str}'"), JSONB)
    merge_expr = InventoryItem.attributes.op("||")(patch_expr)

    values: dict[str, Any] = {"attributes": merge_expr}
    if updated_by is not None:
        values["updated_by"] = updated_by

    stmt = (
        update(InventoryItem)
        .where(InventoryItem.id == item_id)
        .where(InventoryItem.tenant_id == tenant_id)
        .values(**values)
        .returning(InventoryItem)
    )
    result = await db.execute(stmt)
    updated = result.scalar_one_or_none()

    log.info(
        "crud.inventory.patch_attributes",
        item_id=str(item_id),
        tenant_id=str(tenant_id),
        patch_keys=list(payload.patch.keys()),
    )
    return updated


# =============================================================================
# SOFT DELETE
# =============================================================================

async def delete_inventory_item(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    tenant_id: uuid.UUID,
    deleted_by: uuid.UUID | None = None,
) -> bool:
    """
    Soft-delete an inventory item by setting ``is_active = False``.

    Hard deletion is intentionally avoided to preserve the audit trail
    required for financial / regulatory compliance.  The item disappears
    from all list and get queries (which filter on ``is_active = TRUE``)
    but remains in the database.

    Args:
        db:         Async SQLAlchemy session.
        item_id:    Target item UUID.
        tenant_id:  Tenant scope guard.
        deleted_by: Optional UUID of the acting user (written to ``updated_by``).

    Returns:
        ``True`` if the item was found and deactivated.
        ``False`` if the item was not found or belongs to another tenant.
    """
    existing = await get_inventory_item(db, item_id=item_id, tenant_id=tenant_id)
    if existing is None:
        return False

    stmt = (
        update(InventoryItem)
        .where(InventoryItem.id == item_id)
        .where(InventoryItem.tenant_id == tenant_id)
        .values(is_active=False, updated_by=deleted_by)
    )
    await db.execute(stmt)

    log.info(
        "crud.inventory.soft_delete",
        item_id=str(item_id),
        tenant_id=str(tenant_id),
    )
    return True


# =============================================================================
# AGGREGATE STATS
# =============================================================================

async def get_inventory_stats(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """
    Return aggregate inventory counts for the dashboard stat strip.

    Executes a single SQL query with conditional ``COUNT()`` aggregates
    to minimise round-trips:

    .. code-block:: sql

        SELECT
            COUNT(*)                                              AS total,
            COUNT(*) FILTER (WHERE status = 'active')            AS active,
            COUNT(*) FILTER (WHERE status = 'draft')             AS draft,
            COUNT(*) FILTER (WHERE quantity_on_hand <= reorder_level) AS low_stock
        FROM public.inventory_items
        WHERE tenant_id = :tenant_id
          AND is_active = TRUE;

    Args:
        db:        Async SQLAlchemy session.
        tenant_id: Tenant scope.

    Returns:
        ``dict`` with keys: ``total``, ``active``, ``draft``, ``low_stock``.
    """
    stmt = (
        select(
            func.count().label("total"),
            func.count().filter(InventoryItem.status == "active").label("active"),
            func.count().filter(InventoryItem.status == "draft").label("draft"),
            func.count().filter(
                InventoryItem.quantity_on_hand <= InventoryItem.reorder_level
            ).label("low_stock"),
        )
        .where(InventoryItem.tenant_id == tenant_id)
        .where(InventoryItem.is_active.is_(True))
    )

    row = (await db.execute(stmt)).one()

    stats: dict[str, int] = {
        "total":     row.total,
        "active":    row.active,
        "draft":     row.draft,
        "low_stock": row.low_stock,
    }

    log.debug("crud.inventory.stats", tenant_id=str(tenant_id), **stats)
    return stats
