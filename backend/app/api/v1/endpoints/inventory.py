"""
app/api/v1/endpoints/inventory.py
==================================
Phase 3 — Multi-Tenant Asynchronous API Router Engine
       Handloom Inventory Control Ledger Pipelines

NOT CANONICAL — see docs/inventory-architecture.md. This router and
app/api/v1/inventory.py (the "general ERP inventory" module) both read and
write the same `inventory_items` table through two independent,
uncoordinated CRUD modules (this one via crud/crud_inventory.py). Universal
Inventory (/api/v1/universal-inventory, app/api/v1/endpoints/universal_inventory.py)
is the actively developed system of record — new inventory work belongs
there, not here.

This module wires the specialised saree / handloom inventory surface under
the ``/api/v1/inventory`` prefix.  All three endpoints enforce strict
tenancy isolation via the ``X-Tenant-ID`` request header and delegate
persistence to the SQLAlchemy 2.0 async session obtained through the
``get_db`` dependency from ``app.core.database``.

Endpoint surface
----------------
    POST   /api/v1/inventory/saree/               Ingest new saree inventory node
    GET    /api/v1/inventory/saree/               Tenancy-scoped catalog listing
    GET    /api/v1/inventory/saree/filter-attributes/  JSONB astext() attribute query

Auth model
----------
    ``X-Tenant-ID`` header carries the tenant UUID for every request.
    Duplicate SKU detection raises HTTP 400 before any DB write.
    All queries are automatically scoped to the authenticated tenant.

Tenancy Contract
-----------------
    * No cross-tenant data leakage — every SELECT / INSERT is filtered by
      ``tenant_id`` resolved from ``X-Tenant-ID``.
    * UUID injection: the ``id`` field is generated server-side (uuid4) so
      clients never control primary-key assignment.

JSONB attribute filtering (``/filter-attributes/``)
----------------------------------------------------
    Uses SQLAlchemy's ``astext()`` operator on JSONB path subscript syntax::

        TenantSareeInventory.attributes[key].astext() == value

    This translates to Postgres ``attributes->>'key' = 'value'``, which
    is index-eligible on GIN-indexed JSONB columns.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.middleware.tenant_auth import TenantIDDep as TenantDep

from app.core.database import get_db
from app.middleware.rbac import RequirePermission
from app.models.inventory import InventoryItem as TenantSareeInventory
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryListResponse,
    PaginationMeta,
)

# =============================================================================
# Router & Logger Initialisation
# =============================================================================

router = APIRouter()

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__).bind(
    module="handloom_inventory_router",
    api_version="v1",
    domain="multi_tenant_saree_ledger",
)


# =============================================================================
# Internal Dependency Helpers
# =============================================================================

# Typed dependency aliases for concise route signatures
DBDep     = Annotated[AsyncSession, Depends(get_db)]


# =============================================================================
# POST /  — Ingest New Saree Inventory Node
# =============================================================================

@router.post(
    "/",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new saree inventory node into the handloom ledger",
    description=(
        "Creates a new ``TenantSareeInventory`` node for the authenticated tenant. "
        "A server-side UUID v4 is injected as the primary key — clients must NOT "
        "supply an ``id`` field. "
        "Raises ``HTTP 400`` if a record with the same SKU already exists for "
        "the tenant (duplicate-SKU guard, checked before any DB write)."
    ),
    operation_id="ingest_saree_inventory_node",
    response_description=(
        "The persisted saree inventory node with server-generated id and timestamps."
    ),
    dependencies=[Depends(RequirePermission("LegacyInventory", "Saree", "Create"))],
)
async def ingest_inventory_node(
    payload:   InventoryItemCreate,
    tenant_id: TenantDep,
    db:        DBDep,
) -> InventoryItemResponse:
    """
    **POST /api/v1/inventory/saree/**

    Ingests a new handloom saree inventory node for the calling tenant.

    Duplicate SKU Guard
    -------------------
    A pre-flight SELECT checks for an existing ``(tenant_id, sku)`` pair.
    If found, the handler raises ``HTTP 400 Bad Request`` **before** issuing
    any INSERT, returning a descriptive error body to the caller.

    UUID Injection
    --------------
    The server generates a UUID v4 via ``uuid.uuid4()`` and assigns it to
    the ``id`` column.  This prevents clients from controlling primary keys
    and keeps the ledger internally consistent.

    Parameters
    ----------
    payload:
        Validated ``InventoryItemCreate`` request body.  The ``attributes``
        field must include a ``template`` discriminant key
        (``"Manufacturing"`` | ``"Retail"`` | ``"Services"``).
    tenant_id:
        Resolved from the ``X-Tenant-ID`` header by the dependency.
    db:
        Injected async SQLAlchemy session.

    Returns
    -------
    InventoryItemResponse
        The persisted inventory node including server-generated ``id``,
        ``tenant_id``, ``created_at``, and ``updated_at`` fields.

    Raises
    ------
    HTTPException (400)
        When a saree inventory node with the same SKU already exists for
        the authenticated tenant.
    """
    bound_log = log.bind(
        endpoint="ingest_inventory_node",
        tenant_id=str(tenant_id),
        sku=payload.sku,
    )

    # 1. Duplicate SKU pre-flight guard
    dup_stmt = (
        select(TenantSareeInventory.id)
        .where(
            TenantSareeInventory.tenant_id == tenant_id,
            TenantSareeInventory.sku       == payload.sku,
        )
        .limit(1)
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none() is not None:
        bound_log.warning(
            "handloom_inventory.duplicate_sku_rejected",
            sku=payload.sku,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"A saree inventory node with SKU '{payload.sku}' already "
                "exists for this tenant. "
                "Use PATCH /{item_id} to update the existing record."
            ),
        )

    # 2. Materialise ORM node — inject server-side UUID
    attribute_dump: dict[str, Any] = payload.attributes.model_dump()

    node = TenantSareeInventory(
        id               = uuid.uuid4(),
        tenant_id        = tenant_id,
        sku              = payload.sku,
        name             = payload.name,
        description      = payload.description,
        category         = payload.category,
        sub_category     = payload.sub_category,
        brand            = payload.brand,
        tags             = payload.tags,
        unit_price       = payload.unit_price,
        cost_price       = payload.cost_price,
        currency         = payload.currency,
        quantity_on_hand = payload.quantity_on_hand,
        reorder_level    = payload.reorder_level,
        unit_of_measure  = payload.unit_of_measure,
        attributes       = attribute_dump,
        status           = payload.status,
        is_active        = True,
    )

    # 3. Commit to session and refresh
    db.add(node)
    await db.flush()
    await db.refresh(node)

    bound_log.info(
        "handloom_inventory.node_ingested",
        item_id=str(node.id),
        name=node.name,
        template=attribute_dump.get("template"),
    )

    return InventoryItemResponse.model_validate(node)


# =============================================================================
# GET /  — Tenancy-Scoped Catalog Listing Stream
# =============================================================================

@router.get(
    "/",
    response_model=InventoryListResponse,
    summary="Stream tenancy-scoped saree catalog listing",
    description=(
        "Returns a paginated catalog of active handloom saree inventory nodes "
        "strictly scoped to the authenticated tenant via ``X-Tenant-ID``. "
        "An optional ``saree_type`` query parameter applies a case-insensitive "
        "ILIKE filter against the ``category`` column."
    ),
    operation_id="list_saree_catalog",
    response_description=(
        "Paginated list of saree inventory nodes for the authenticated tenant."
    ),
    dependencies=[Depends(RequirePermission("LegacyInventory", "Saree", "Read"))],
)
async def list_saree_catalog(
    tenant_id:  TenantDep,
    db:         DBDep,
    saree_type: Annotated[
        Optional[str],
        Query(
            description=(
                "Optional case-insensitive saree type filter. "
                "Matched against the ``category`` column using ILIKE syntax "
                "(e.g. ``saree_type=kanjivaram`` matches 'Kanjivaram', 'KANJIVARAM', etc.). "
                "Omit to return all active nodes for the tenant."
            ),
            max_length=128,
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=200, description="Page size (1-200). Default: 50."),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Zero-based page offset. Default: 0."),
    ] = 0,
) -> InventoryListResponse:
    """
    **GET /api/v1/inventory/saree/**

    Streams a tenancy-scoped catalog of handloom saree inventory nodes.

    Tenancy Isolation
    -----------------
    The query is hard-filtered by ``tenant_id`` derived from the
    ``X-Tenant-ID`` header.  No cross-tenant data can leak regardless of
    other filter parameters.

    saree_type Filter
    -----------------
    When supplied, ``saree_type`` is applied via SQLAlchemy's ``ilike()``
    operator against the ``category`` column::

        TenantSareeInventory.category.ilike(f"%{saree_type}%")

    This resolves to Postgres ``category ILIKE '%<value>%'`` — a
    case-insensitive substring match.

    Parameters
    ----------
    tenant_id:
        Resolved from the ``X-Tenant-ID`` header.
    db:
        Injected async SQLAlchemy session.
    saree_type:
        Optional case-insensitive ILIKE match against ``category``.
    limit:
        Page size. Range 1-200.
    offset:
        Zero-based record offset for pagination.

    Returns
    -------
    InventoryListResponse
        Paginated items list and ``PaginationMeta`` block.
    """
    bound_log = log.bind(
        endpoint="list_saree_catalog",
        tenant_id=str(tenant_id),
        saree_type=saree_type,
        limit=limit,
        offset=offset,
    )

    # Base tenancy-scoped filter predicate
    base_conditions = [
        TenantSareeInventory.tenant_id == tenant_id,
        TenantSareeInventory.is_active.is_(True),
    ]

    # Optional case-insensitive saree_type ilike filter
    if saree_type is not None:
        base_conditions.append(
            TenantSareeInventory.category.ilike(f"%{saree_type}%")
        )

    # Count query (total rows, respecting all filters)
    count_stmt = (
        select(sa_func.count(TenantSareeInventory.id))
        .where(*base_conditions)
    )
    total_result = await db.execute(count_stmt)
    total: int = total_result.scalar_one()

    # Data query with pagination, ordered by most recently updated
    data_stmt = (
        select(TenantSareeInventory)
        .where(*base_conditions)
        .order_by(TenantSareeInventory.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    data_result = await db.execute(data_stmt)
    nodes: list[TenantSareeInventory] = list(data_result.scalars().all())

    bound_log.info(
        "handloom_inventory.catalog_streamed",
        total=total,
        returned=len(nodes),
    )

    return InventoryListResponse(
        items=[InventoryItemResponse.model_validate(n) for n in nodes],
        meta=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(nodes)) < total,
        ),
    )


# =============================================================================
# GET /filter-attributes/  — Advanced JSONB astext() Attribute Query Engine
# =============================================================================

@router.get(
    "/filter-attributes/",
    response_model=InventoryListResponse,
    summary="Advanced JSONB attribute filter using astext() extraction",
    description=(
        "Performs advanced queries on internal JSONB ``attributes`` fields using "
        "PostgreSQL's text-extraction syntax via SQLAlchemy's ``astext()`` operator: "
        "``TenantSareeInventory.attributes[key].astext() == value``. "
        "Resolves to ``attributes->>'key' = 'value'`` in Postgres. "
        "Strictly scoped to the authenticated tenant via ``X-Tenant-ID``."
    ),
    operation_id="filter_saree_by_jsonb_attributes",
    response_description=(
        "Paginated list of saree inventory nodes matching the JSONB attribute predicate."
    ),
    dependencies=[Depends(RequirePermission("LegacyInventory", "Saree", "Read"))],
)
async def filter_by_jsonb_attributes(
    tenant_id:       TenantDep,
    db:              DBDep,
    attribute_key:   Annotated[
        str,
        Query(
            alias="key",
            min_length=1,
            max_length=128,
            description=(
                "Top-level JSONB key inside the ``attributes`` column to filter on. "
                "Examples: ``template``, ``color``, ``material``, ``quality_grade``."
            ),
        ),
    ],
    attribute_value: Annotated[
        str,
        Query(
            alias="value",
            min_length=1,
            max_length=512,
            description=(
                "Exact string value to match against ``attributes[key]`` via "
                "Postgres ``astext()`` (``->>``) extraction. Case-sensitive."
            ),
        ),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=200, description="Page size (1-200). Default: 50."),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Zero-based page offset. Default: 0."),
    ] = 0,
) -> InventoryListResponse:
    """
    **GET /api/v1/inventory/saree/filter-attributes/**

    Advanced JSONB attribute query engine for the handloom saree ledger.

    JSONB Text Extraction
    ---------------------
    Queries are built with SQLAlchemy's subscript + ``astext()`` syntax::

        TenantSareeInventory.attributes[key].astext() == value

    This resolves to the Postgres expression::

        attributes->>'key' = 'value'

    The ``->>`` operator extracts a JSONB value as ``text``, enabling
    equality comparison and leveraging GIN index acceleration on the
    ``attributes`` column.

    Example Calls
    -------------
    Filter by industry template::

        GET /filter-attributes/?key=template&value=Retail

    Filter by weave quality grade::

        GET /filter-attributes/?key=quality_grade&value=A

    Filter by material::

        GET /filter-attributes/?key=material&value=Pure%20Silk

    Parameters
    ----------
    tenant_id:
        Resolved from ``X-Tenant-ID`` — enforces tenancy isolation.
    db:
        Injected async SQLAlchemy session.
    attribute_key:
        Top-level JSONB key to query (query param alias: ``key``).
    attribute_value:
        Exact string value matched via ``astext()`` (query param alias: ``value``).
    limit:
        Page size. Range 1-200.
    offset:
        Zero-based record offset for pagination.

    Returns
    -------
    InventoryListResponse
        Paginated items list and ``PaginationMeta`` block.

    Raises
    ------
    HTTPException (422)
        If ``key`` or ``value`` query parameters fail length validation.
    """
    bound_log = log.bind(
        endpoint="filter_by_jsonb_attributes",
        tenant_id=str(tenant_id),
        attribute_key=attribute_key,
        attribute_value=attribute_value,
        limit=limit,
        offset=offset,
    )

    # JSONB astext() predicate
    # Translates to SQL:  attributes->>'key' = 'value'
    jsonb_text_predicate = (
        TenantSareeInventory.attributes[attribute_key].astext() == attribute_value
    )

    # Combined WHERE clause
    where_conditions = [
        TenantSareeInventory.tenant_id == tenant_id,
        TenantSareeInventory.is_active.is_(True),
        jsonb_text_predicate,
    ]

    # Count query
    count_stmt = (
        select(sa_func.count(TenantSareeInventory.id))
        .where(*where_conditions)
    )
    total_result = await db.execute(count_stmt)
    total: int = total_result.scalar_one()

    # Data query with pagination
    data_stmt = (
        select(TenantSareeInventory)
        .where(*where_conditions)
        .order_by(TenantSareeInventory.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    data_result = await db.execute(data_stmt)
    nodes: list[TenantSareeInventory] = list(data_result.scalars().all())

    bound_log.info(
        "handloom_inventory.jsonb_filter_executed",
        total=total,
        returned=len(nodes),
        jsonb_path=f"attributes->>{attribute_key!r}",
        match_value=attribute_value,
    )

    return InventoryListResponse(
        items=[InventoryItemResponse.model_validate(n) for n in nodes],
        meta=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(nodes)) < total,
        ),
    )
