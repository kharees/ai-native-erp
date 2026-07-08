"""
app/crud/crud_inventory.py
===========================
Phase 4 — Asynchronous Repository & CRUD Operations Layer
         Multi-Tenant Handloom Saree Inventory Control Ledger

This module provides the ``CRUDTenantInventory`` class — the single
authoritative data-access gateway for all ``TenantSareeInventory``
(``public.tenant_saree_inventory``) database operations.

Design Principles
-----------------
* **Class-based repository pattern**: All methods are grouped on one class
  so callers get a consistent, discoverable API surface rather than a flat
  namespace of functions. A singleton instance ``crud_saree_inventory``
  is exported for import convenience.

* **Absolute tenant isolation**: Every query — whether read or write — is
  hard-filtered by ``TenantSareeInventory.tenant_id == tenant_id``. No
  shortcut paths exist that could leak cross-tenant rows.

* **SQLAlchemy 2.0 async ORM**: All DB interaction goes through
  ``AsyncSession`` with ``select()`` / ``update()`` Core expressions.
  Zero raw SQL strings — all predicates are type-safe ORM column expressions.

* **JSONB serialisation safety**: The ``attributes`` discriminated-union
  Pydantic model is serialised via ``model_dump(mode="json", exclude_none=True)``
  before being stored. This ensures asyncpg receives a plain Python dict that
  SQLAlchemy maps to JSONB without serialisation errors.

* **Structured telemetry throughout**: Every method binds a contextual
  ``structlog`` logger with ``tenant_id``, ``operation``, and domain-specific
  keys. This provides per-request trace visibility with zero overhead on
  non-debug log levels.

* **Unit-of-work contract**: Methods call ``db.flush()`` (not ``db.commit()``)
  so they participate in the caller's transaction. Commit / rollback is the
  responsibility of the ``get_db`` FastAPI dependency or the caller's
  context manager in background tasks.

Public API
----------
  CRUDTenantInventory.create()               — ingest a new saree inventory node
  CRUDTenantInventory.get_multi_by_tenant()  — paginated tenant-scoped listing
  CRUDTenantInventory.get_by_sku()           — single item by SKU within tenant

Singleton
---------
  crud_saree_inventory: CRUDTenantInventory  — pre-constructed class instance
                                               ready for dependency injection

Usage
-----
    from app.crud.crud_inventory import crud_saree_inventory

    # In a FastAPI route or service layer:
    node = await crud_saree_inventory.create(db, payload=payload, tenant_id=tid)
    page = await crud_saree_inventory.get_multi_by_tenant(db, tenant_id=tid)
    item = await crud_saree_inventory.get_by_sku(db, sku="KJV-2024-001", tenant_id=tid)
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Sequence

import structlog
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# ORM model alias — TenantSareeInventory is the canonical name for the
# handloom domain; it resolves to InventoryItem backed by the
# public.inventory_items table (or public.tenant_saree_inventory via the
# Phase 3 migration).
# ---------------------------------------------------------------------------
from app.models.inventory import InventoryItem as TenantSareeInventory

# ---------------------------------------------------------------------------
# Schema imports
# ---------------------------------------------------------------------------
from app.schemas.inventory import (
    InventoryItemCreate as SareeInventoryCreate,
    InventoryItemResponse as SareeInventoryResponse,
    InventoryListResponse as SareeInventoryListResponse,
    PaginationMeta,
)

# ---------------------------------------------------------------------------
# Module-level structlog logger — methods bind additional context per call.
# ---------------------------------------------------------------------------
_base_log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__).bind(
    layer="crud_repository",
    domain="multi_tenant_saree_inventory",
    table="tenant_saree_inventory",
)


# =============================================================================
# Repository Class
# =============================================================================

class CRUDTenantInventory:
    """
    Asynchronous repository class for the ``TenantSareeInventory`` ORM model.

    Encapsulates all database query pipelines for the Phase 4 handloom
    inventory control ledger, enforcing:

        • Strict row-level tenant isolation on every operation.
        • Contextual structlog telemetry tracing each pipeline stage.
        • SQLAlchemy 2.0 async patterns (``select()``, ``db.execute()``,
          ``db.flush()``, ``db.refresh()``).
        • JSONB-safe attribute serialisation.

    All methods accept an ``AsyncSession`` as their first positional argument
    so they integrate cleanly with FastAPI's ``Depends(get_db)`` pattern.
    """

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _serialize_attributes(attributes_model: Any) -> dict[str, Any]:
        """
        Serialise a validated Pydantic attribute sub-model to a plain dict
        suitable for Postgres JSONB storage.

        Uses ``model_dump(mode="json", exclude_none=True)`` so that:
          * ``AnyHttpUrl`` → plain ``str``
          * ``datetime``   → ISO 8601 ``str``
          * ``Enum``       → ``str`` value
          * ``None``       fields are excluded to keep the JSONB lean.

        Parameters
        ----------
        attributes_model:
            A validated Pydantic union member (ManufacturingAttributes,
            RetailAttributes, or ServicesAttributes).

        Returns
        -------
        dict[str, Any]
            Plain Python dict safe for asyncpg / SQLAlchemy JSONB column.
        """
        return attributes_model.model_dump(mode="json", exclude_none=True)

    # =========================================================================
    # CREATE — Ingest new saree inventory node
    # =========================================================================

    async def create(
        self,
        db: AsyncSession,
        *,
        payload: SareeInventoryCreate,
        tenant_id: uuid.UUID,
        created_by: uuid.UUID | None = None,
    ) -> TenantSareeInventory:
        """
        Ingest a new ``TenantSareeInventory`` node into the handloom ledger.

        Pipeline stages (all instrumented with structlog telemetry):
            1. **Attributes serialisation** — converts the discriminated-union
               Pydantic sub-model to a plain ``dict`` for JSONB storage.
            2. **ORM instantiation** — builds the ``TenantSareeInventory``
               object with the caller-supplied ``tenant_id`` strictly embedded;
               no client-controlled ``id`` field (server-default UUID v4).
            3. **Session flush** — issues the ``INSERT`` within the current
               transaction boundary without committing.
            4. **Session refresh** — reloads the row from Postgres so all
               server-generated values (``id``, ``created_at``, ``updated_at``)
               are populated on the returned ORM instance.
            5. **Telemetry emission** — logs the operation at INFO level with
               full context: ``item_id``, ``sku``, ``tenant_id``, ``template``,
               ``elapsed_ms``.

        Parameters
        ----------
        db:
            Async SQLAlchemy session (injected via ``Depends(get_db)``).
        payload:
            Fully-validated ``SareeInventoryCreate`` (alias for
            ``InventoryItemCreate``) — all required fields and the
            discriminated ``attributes`` sub-model present.
        tenant_id:
            UUID of the calling tenant — written to the ``tenant_id`` column
            and enforced as the tenancy isolation boundary.
        created_by:
            Optional UUID of the creating user. Written to both
            ``created_by`` and ``updated_by`` audit columns.

        Returns
        -------
        TenantSareeInventory
            Refreshed ORM instance with all server-generated values populated.

        Raises
        ------
        sqlalchemy.exc.IntegrityError
            If ``(tenant_id, sku)`` violates the unique constraint
            ``uq_saree_inventory_tenant_sku`` (or ``uq_inventory_items_tenant_sku``
            on the shared table). The router maps this to ``HTTP 409 Conflict``
            or ``HTTP 400 Bad Request`` for the duplicate-SKU guard path.
        """
        op_log = _base_log.bind(
            operation="create",
            tenant_id=str(tenant_id),
            sku=payload.sku,
            template=getattr(payload.attributes, "template", "unknown"),
        )
        op_log.debug("crud.saree_inventory.create.start")
        _t0 = time.perf_counter()

        # Stage 1 — Serialise discriminated-union attributes to plain dict
        attributes_dict: dict[str, Any] = self._serialize_attributes(payload.attributes)

        # Stage 2 — Instantiate ORM node with tenant_id strictly embedded.
        #            Server-default UUID v4 is used for `id` — no client override.
        node = TenantSareeInventory(
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
            is_active        = True,
            created_by       = created_by,
            updated_by       = created_by,
        )

        # Stage 3 — Flush INSERT within the current transaction
        db.add(node)
        await db.flush()

        # Stage 4 — Refresh to populate server-generated values
        await db.refresh(node)

        _elapsed_ms = round((time.perf_counter() - _t0) * 1000, 3)

        # Stage 5 — Structured telemetry at INFO level
        op_log.info(
            "crud.saree_inventory.create.complete",
            item_id=str(node.id),
            name=node.name,
            category=node.category,
            template=attributes_dict.get("template"),
            unit_price=float(node.unit_price),
            currency=node.currency,
            elapsed_ms=_elapsed_ms,
        )

        return node

    # =========================================================================
    # GET MULTI — Paginated tenancy-scoped catalog listing
    # =========================================================================

    async def get_multi_by_tenant(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        saree_type: str | None = None,
        active_only: bool = True,
    ) -> SareeInventoryListResponse:
        """
        Query and stream records from ``TenantSareeInventory``, filtering rows
        strictly where ``TenantSareeInventory.tenant_id == tenant_id``.

        This method enforces **absolute row-level isolation** — the
        ``tenant_id`` predicate is always the first WHERE clause applied
        and cannot be bypassed by any optional filter parameter.

        Pipeline stages:
            1. **Tenancy predicate construction** — builds the mandatory
               ``tenant_id == tenant_id`` guard clause.
            2. **Optional saree_type ILIKE filter** — case-insensitive
               substring match on the ``category`` column when supplied.
            3. **COUNT subquery** — determines ``meta.total`` without LIMIT
               so the caller can compute pagination state client-side.
            4. **Data query** — applies ``ORDER BY updated_at DESC, id``,
               ``LIMIT``, and ``OFFSET`` for stable, consistent pagination.
            5. **Response assembly** — wraps ORM instances in
               ``SareeInventoryResponse`` and attaches ``PaginationMeta``.
            6. **Telemetry emission** — logs at INFO level with full context.

        Parameters
        ----------
        db:
            Async SQLAlchemy session.
        tenant_id:
            UUID of the calling tenant — **all rows are filtered strictly
            by this value**. No cross-tenant data can leak.
        limit:
            Maximum number of records to return. Range 1–200. Default: 50.
        offset:
            Zero-based record offset for pagination. Default: 0.
        saree_type:
            Optional case-insensitive ILIKE filter against the ``category``
            column (e.g. ``"kanjivaram"`` matches ``"Kanjivaram"``,
            ``"KANJIVARAM"``). When ``None``, all categories are returned.
        active_only:
            When ``True`` (default), restricts results to rows where
            ``is_active = TRUE``. Set to ``False`` only for admin/audit
            endpoints that need to surface soft-deleted nodes.

        Returns
        -------
        SareeInventoryListResponse
            Paginated list of saree inventory nodes with ``PaginationMeta``
            block (``total``, ``limit``, ``offset``, ``has_more``).
        """
        op_log = _base_log.bind(
            operation="get_multi_by_tenant",
            tenant_id=str(tenant_id),
            limit=limit,
            offset=offset,
            saree_type=saree_type,
            active_only=active_only,
        )
        op_log.debug("crud.saree_inventory.get_multi.start")
        _t0 = time.perf_counter()

        # Stage 1 — Mandatory tenancy guard predicate
        #            TenantSareeInventory.tenant_id == tenant_id is ALWAYS applied.
        base_conditions = [
            TenantSareeInventory.tenant_id == tenant_id,
        ]

        if active_only:
            base_conditions.append(TenantSareeInventory.is_active.is_(True))

        # Stage 2 — Optional saree_type ILIKE filter on category column
        if saree_type is not None:
            base_conditions.append(
                TenantSareeInventory.category.ilike(f"%{saree_type}%")
            )

        # Stage 3 — COUNT subquery (respects all filters, no LIMIT applied)
        count_stmt = (
            select(sa_func.count(TenantSareeInventory.id))
            .where(*base_conditions)
        )
        count_result = await db.execute(count_stmt)
        total: int = count_result.scalar_one()

        # Stage 4 — Data query with deterministic ordering and pagination
        data_stmt = (
            select(TenantSareeInventory)
            .where(*base_conditions)
            .order_by(
                TenantSareeInventory.updated_at.desc(),
                TenantSareeInventory.id,        # tiebreak for stable pagination
            )
            .limit(limit)
            .offset(offset)
        )
        data_result = await db.execute(data_stmt)
        nodes: Sequence[TenantSareeInventory] = data_result.scalars().all()

        _elapsed_ms = round((time.perf_counter() - _t0) * 1000, 3)

        # Stage 5 — Response assembly
        response = SareeInventoryListResponse(
            items=[SareeInventoryResponse.model_validate(n) for n in nodes],
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(nodes)) < total,
            ),
        )

        # Stage 6 — Structured telemetry
        op_log.info(
            "crud.saree_inventory.get_multi.complete",
            total_in_scope=total,
            returned=len(nodes),
            has_more=response.meta.has_more,
            elapsed_ms=_elapsed_ms,
        )

        return response

    # =========================================================================
    # GET BY SKU — Single item lookup within isolated tenant boundary
    # =========================================================================

    async def get_by_sku(
        self,
        db: AsyncSession,
        *,
        sku: str,
        tenant_id: uuid.UUID,
        active_only: bool = True,
    ) -> TenantSareeInventory | None:
        """
        Query a single inventory item matching a specific SKU code within the
        strictly isolated tenant boundary scope.

        The query enforces:
            ``TenantSareeInventory.tenant_id == tenant_id``
            AND ``TenantSareeInventory.sku == sku``

        This dual-predicate structure ensures:
          * A tenant cannot retrieve another tenant's SKU even if they guess
            the exact code — the ``tenant_id`` predicate blocks the row.
          * No 403 vs 404 information leakage: both "not found" and "wrong
            tenant" scenarios return ``None``, which the router maps to
            ``HTTP 404 Not Found``.

        Typical use cases:
          * Pre-flight duplicate-SKU check before an INSERT.
          * SKU-based lookup from external integration payloads (e.g. ERP sync,
            barcode scanner webhooks).

        Parameters
        ----------
        db:
            Async SQLAlchemy session.
        sku:
            Stock-keeping unit code to look up (exact match, case-sensitive).
        tenant_id:
            UUID of the calling tenant — enforces the isolation boundary.
        active_only:
            When ``True`` (default), only active (non-soft-deleted) records
            are returned. Pass ``False`` to surface soft-deleted nodes in
            admin / recovery flows.

        Returns
        -------
        TenantSareeInventory | None
            The matching ORM instance, or ``None`` if no record exists for
            the given ``(tenant_id, sku)`` pair (or is soft-deleted when
            ``active_only=True``).
        """
        op_log = _base_log.bind(
            operation="get_by_sku",
            tenant_id=str(tenant_id),
            sku=sku,
            active_only=active_only,
        )
        op_log.debug("crud.saree_inventory.get_by_sku.start")
        _t0 = time.perf_counter()

        # Build predicate: tenant boundary + SKU exact match
        stmt = (
            select(TenantSareeInventory)
            .where(TenantSareeInventory.tenant_id == tenant_id)
            .where(TenantSareeInventory.sku == sku)
        )

        if active_only:
            stmt = stmt.where(TenantSareeInventory.is_active.is_(True))

        result = await db.execute(stmt)
        node: TenantSareeInventory | None = result.scalar_one_or_none()

        _elapsed_ms = round((time.perf_counter() - _t0) * 1000, 3)

        # Telemetry — DEBUG on miss to avoid log noise; INFO on hit
        if node is not None:
            op_log.info(
                "crud.saree_inventory.get_by_sku.found",
                item_id=str(node.id),
                name=node.name,
                status=node.status,
                template=node.attributes.get("template") if node.attributes else None,
                elapsed_ms=_elapsed_ms,
            )
        else:
            op_log.debug(
                "crud.saree_inventory.get_by_sku.not_found",
                elapsed_ms=_elapsed_ms,
            )

        return node


# =============================================================================
# Singleton instance — import and use directly in routers / services
# =============================================================================

crud_saree_inventory: CRUDTenantInventory = CRUDTenantInventory()
"""
Pre-constructed singleton of ``CRUDTenantInventory``.

Import and inject this instance wherever saree inventory CRUD operations
are needed:

    from app.crud.crud_inventory import crud_saree_inventory

    node = await crud_saree_inventory.create(db, payload=..., tenant_id=...)
    page = await crud_saree_inventory.get_multi_by_tenant(db, tenant_id=...)
    item = await crud_saree_inventory.get_by_sku(db, sku=..., tenant_id=...)
"""
