"""
app/middleware/tenant_auth.py
==============================
Phase 5 — Global Multi-Tenant Authentication & Route Protection
          Security Middleware Framework

Overview
--------
This module provides two complementary components that together form the
complete tenant security enforcement layer for every inbound HTTP request:

    1. ``TenantAuthMiddleware``  — Starlette ``BaseHTTPMiddleware`` subclass
       that intercepts **every** incoming request at the ASGI transport layer,
       before any FastAPI route handler or dependency executes.

    2. ``get_verified_tenant_id`` — FastAPI dependency function that surfaces
       the already-validated tenant UUID from ``request.state`` into route
       signatures as a typed, trusted parameter.

Security Model
--------------
The middleware enforces a two-tier response matrix:

    • **401 Unauthorized** — ``X-Tenant-ID`` header is absent entirely.
      Signals the client that authentication context is required.

    • **403 Forbidden** — ``X-Tenant-ID`` header is present but:
        - Is not a well-formed UUID.
        - Does not match any row in ``public.tenants``.
        - Matches a tenant record where ``is_active = FALSE``.
      Signals the client that the supplied credential is rejected.

    • **500 Internal Server Error** — Database probe failed unexpectedly.
      The middleware catches all unexpected exceptions, logs the full
      traceback via structlog, and returns a safe generic error body
      without leaking internal details.

Bypass Route Registry
---------------------
Certain paths are exempt from tenant validation (system health probes,
OpenAPI schema endpoints, CORS pre-flight). These are configured in
``_BYPASS_PATHS`` and ``_BYPASS_PREFIXES`` and can be extended without
modifying the middleware logic itself.

Context Propagation
-------------------
For every request that passes validation, the middleware writes to
``request.state``:

    request.state.tenant_id   : uuid.UUID   — validated tenant UUID
    request.state.tenant_slug : str         — human-readable tenant slug
    request.state.tenant_plan : str         — subscription plan label

And extends the ``structlog.contextvars`` binding (shared with the
``request_logging_middleware`` in main.py) with:

    tenant_id   = str(tenant_id)
    tenant_slug = slug

This means every subsequent log call within the same asyncio task
automatically carries full tenant context — zero boilerplate in
route handlers.

Row-Level Isolation Role
------------------------
The middleware acts as the **application-layer enforcement point** that
sits in front of the Postgres RLS policies defined in the Alembic migration.
Together they form a defence-in-depth stack:

    Layer 1 (this middleware) → rejects requests with invalid/missing tenant
    Layer 2 (CRUD repository) → always filters by tenant_id in WHERE clauses
    Layer 3 (Postgres RLS)    → server-side row filter via auth.uid()

Wiring into main.py
-------------------
Register the middleware **after** CORSMiddleware and **before** any routers:

    from app.middleware.tenant_auth import TenantAuthMiddleware

    app.add_middleware(TenantAuthMiddleware)

Or equivalently (Starlette registration order note: add_middleware() applies
in reverse — last added runs first):

    # In main.py middleware stack section:
    app.add_middleware(TenantAuthMiddleware)   # innermost — runs after CORS

FastAPI Dependency Usage
------------------------
In route handlers that need the tenant UUID as a typed parameter:

    from app.middleware.tenant_auth import TenantIDDep

    @router.get("/")
    async def my_route(tenant_id: TenantIDDep, db: DBDep) -> ...:
        ...
"""

from __future__ import annotations

import time
import uuid
from typing import Annotated, Callable, Sequence

import structlog
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.database import AsyncSessionLocal
from app.models.tenants import Tenant
from app.models.users import UserProfile
from app.models.sessions import TenantSession
from jose import JWTError, jwt
from app.core.config import settings

# ---------------------------------------------------------------------------
# Module-level structlog logger
# ---------------------------------------------------------------------------
log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__).bind(
    layer="security_middleware",
    component="TenantAuthMiddleware",
)


# =============================================================================
# 1.  Bypass Route Registry
#     Paths and prefixes listed here skip tenant header validation.
#     Add new public endpoints here; never bypass /api/v1/* routes.
# =============================================================================

#: Exact path matches that bypass tenant auth (system probes, root).
_BYPASS_PATHS: frozenset[str] = frozenset({
    "/",
    "/health",
    "/health/detailed",
})

#: Prefix matches that bypass tenant auth (OpenAPI / Swagger UI assets).
_BYPASS_PREFIXES: tuple[str, ...] = (
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/api/v1/auth",
)

#: HTTP methods that are always passed through (CORS pre-flight).
_BYPASS_METHODS: frozenset[str] = frozenset({"OPTIONS"})


def _is_bypass_route(request: Request) -> bool:
    """
    Return ``True`` if the given request is exempt from tenant auth validation.

    Bypass conditions (evaluated in order):
        1. HTTP method is OPTIONS (CORS pre-flight).
        2. Path is in ``_BYPASS_PATHS`` (exact match).
        3. Path starts with any prefix in ``_BYPASS_PREFIXES``.

    Parameters
    ----------
    request:
        The incoming Starlette ``Request`` object.

    Returns
    -------
    bool
        ``True`` if the request should bypass tenant header validation.
    """
    if request.method in _BYPASS_METHODS:
        return True
    path = request.url.path
    if path in _BYPASS_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _BYPASS_PREFIXES)


# =============================================================================
# 2.  Tenant Validation Query
#     Executes a single lightweight SELECT against public.tenants.
#     Returns (id, slug, plan) tuple or None.
# =============================================================================

async def _validate_tenant(
    tenant_uuid: uuid.UUID,
    user_uuid: uuid.UUID | None,
    session_uuid: uuid.UUID | None = None
) -> tuple[uuid.UUID, str, str] | None:
    """
    Query ``public.tenants`` for an active tenant matching ``tenant_uuid``.
    If user_uuid is provided, ensures user is active.
    If session_uuid is provided, ensures session is active.
    """
    stmt = (
        select(
            Tenant.id,
            Tenant.slug,
            Tenant.plan,
        )
        .where(Tenant.id == tenant_uuid)
        .where(Tenant.is_active.is_(True))
    )
    
    if user_uuid:
        stmt = stmt.join(UserProfile, UserProfile.tenant_id == Tenant.id).where(
            UserProfile.user_id == user_uuid
        ).where(UserProfile.is_active.is_(True))
        
    if session_uuid:
        stmt = stmt.join(TenantSession, TenantSession.tenant_id == Tenant.id).where(
            TenantSession.id == session_uuid
        )
        
    stmt = stmt.limit(1)

    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
        row = result.one_or_none()
        
        # If valid and a session was provided, opportunistically update last_active_at
        if row and session_uuid:
            from sqlalchemy import update
            from datetime import datetime, timezone
            update_stmt = update(TenantSession).where(TenantSession.id == session_uuid).values(last_active_at=datetime.now(timezone.utc))
            await session.execute(update_stmt)
            await session.commit()

    if row is None:
        return None
    return (row.id, row.slug, row.plan)


# =============================================================================
# 3.  JSON Error Response Builders
#     Produce consistent, structured error bodies that match the project's
#     existing error response contract (detail string + request_id).
# =============================================================================

def _build_401(request: Request, detail: str) -> JSONResponse:
    """
    Build an HTTP 401 Unauthorized ``JSONResponse``.

    Used when the ``X-Tenant-ID`` header is missing entirely — the client
    has not supplied the required authentication context.

    Parameters
    ----------
    request:
        Incoming request (used to attach ``request_id`` to the error body).
    detail:
        Human-readable error message.
    """
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error":      "tenant_authentication_required",
            "detail":     detail,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
        headers={"WWW-Authenticate": "TenantID"},
    )


def _build_403(request: Request, detail: str) -> JSONResponse:
    """
    Build an HTTP 403 Forbidden ``JSONResponse``.

    Used when the ``X-Tenant-ID`` header is present but the tenant UUID is
    malformed, not found in the registry, or belongs to an inactive tenant.

    Parameters
    ----------
    request:
        Incoming request.
    detail:
        Human-readable rejection reason (safe — no internal DB details leaked).
    """
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error":      "tenant_access_denied",
            "detail":     detail,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


def _build_500(request: Request) -> JSONResponse:
    """
    Build an HTTP 500 Internal Server Error ``JSONResponse``.

    Used when the tenant validation DB query raises an unexpected exception.
    The body contains no internal detail — error is fully logged server-side.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error":      "tenant_auth_service_error",
            "detail":     "An internal error occurred during tenant authentication.",
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


# =============================================================================
# 4.  TenantAuthMiddleware — Core ASGI Middleware Class
# =============================================================================

class TenantAuthMiddleware(BaseHTTPMiddleware):
    """
    Global multi-tenant authentication and route protection security middleware.

    Intercepts **every** incoming HTTP request at the ASGI transport layer
    and enforces the following pipeline before any route handler executes:

    Pipeline
    --------
    ::

        Request arrives
            │
            ├─► Bypass check (health probes, docs, OPTIONS)
            │       └─► Pass through immediately (no DB query)
            │
            ├─► Extract X-Tenant-ID header
            │       └─► Missing → 401 Unauthorized
            │
            ├─► Parse header value as UUID
            │       └─► Invalid UUID format → 403 Forbidden
            │
            ├─► Query public.tenants WHERE id=:uuid AND is_active=TRUE
            │       ├─► DB error → 500 Internal Server Error (logged)
            │       └─► Row not found / inactive → 403 Forbidden
            │
            ├─► Bind tenant context
            │       ├─► request.state.tenant_id   = uuid.UUID
            │       ├─► request.state.tenant_slug = str
            │       ├─► request.state.tenant_plan = str
            │       └─► structlog.contextvars extended with tenant_id, tenant_slug
            │
            └─► Call next handler (route executes with full tenant context)

    Error Response Contract
    -----------------------
    All error responses are ``JSONResponse`` objects with:

        {
            "error":      "<machine_readable_code>",
            "detail":     "<human_readable_message>",
            "request_id": "<uuid_from_state>"
        }

    This matches the existing global exception handler in ``main.py``.

    Telemetry
    ---------
    Every pipeline stage emits a structured log event via ``structlog``:

    +--------------------------+-------+-----------------------------------+
    | Event key                | Level | When                              |
    +==========================+=======+===================================+
    | tenant_auth.bypass       | DEBUG | Request exempted from validation  |
    | tenant_auth.header_missing| WARN | X-Tenant-ID header absent         |
    | tenant_auth.invalid_uuid | WARN  | Header present, not a valid UUID  |
    | tenant_auth.db_error     | ERROR | DB validation query failed        |
    | tenant_auth.not_found    | WARN  | Tenant UUID not in active registry|
    | tenant_auth.granted      | INFO  | Tenant validated, context bound   |
    | tenant_auth.complete     | DEBUG | Full pipeline timing               |
    +--------------------------+-------+-----------------------------------+
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        log.info(
            "tenant_auth.middleware_registered",
            bypass_paths=sorted(_BYPASS_PATHS),
            bypass_prefixes=list(_BYPASS_PREFIXES),
        )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Main middleware dispatch — called for every HTTP request.

        Parameters
        ----------
        request:
            Incoming Starlette ``Request`` object. Provides access to
            headers, method, URL path, and ``request.state``.
        call_next:
            ASGI callable that invokes the next middleware or route handler.

        Returns
        -------
        Response
            Either an error ``JSONResponse`` (401 / 403 / 500) or the
            ``Response`` produced by the downstream route handler.
        """
        _t0 = time.perf_counter()

        # Derive request_id for all log calls in this dispatch.
        # May be set by request_logging_middleware (runs before this in
        # main.py's add_middleware stack, since it is registered later).
        request_id: str = getattr(request.state, "request_id", "unknown")

        bound = log.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # ── Stage 1: Bypass check ─────────────────────────────────────────────
        if _is_bypass_route(request):
            bound.debug(
                "tenant_auth.bypass",
                reason="exempt_route",
            )
            return await call_next(request)

        # ── Stage 2: Extract JWT Token ────────────────────────────────────────
        auth_header: str | None = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            bound.warning(
                "tenant_auth.token_missing",
                header="Authorization",
                action="reject_401",
            )
            return _build_401(
                request,
                detail="Missing or invalid Authorization header. Expected 'Bearer <token>'.",
            )

        token = auth_header[len("Bearer "):]

        # ── Stage 3: Parse JWT and Extract Tenant ID ──────────────────────────
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            
            # Try to get tenant_id from claims first, fallback to header if allowed
            app_metadata = payload.get("app_metadata", {})
            user_metadata = payload.get("user_metadata", {})
            
            raw_tenant_id = app_metadata.get("tenant_id") or user_metadata.get("tenant_id")
            
            header_tenant_id = request.headers.get("X-Tenant-ID")
            
            if raw_tenant_id and header_tenant_id and raw_tenant_id != header_tenant_id:
                bound.warning("tenant_auth.tenant_mismatch", action="reject_403")
                return _build_403(
                    request,
                    detail="X-Tenant-ID header does not match the tenant ID in the JWT.",
                )
                
            if not raw_tenant_id:
                raw_tenant_id = header_tenant_id
                if not raw_tenant_id:
                    bound.warning(
                        "tenant_auth.missing_tenant_claim",
                        action="reject_403",
                    )
                    return _build_403(
                        request,
                        detail="No tenant_id claim found in JWT and no X-Tenant-ID header provided.",
                    )
                if not payload.get("sub"):
                    bound.warning("tenant_auth.insecure_fallback", action="reject_403")
                    return _build_403(
                        request,
                        detail="X-Tenant-ID fallback requires a user context (sub claim) in JWT.",
                    )

            tenant_uuid = uuid.UUID(raw_tenant_id)
            user_id = payload.get("sub")
            if user_id:
                request.state.user_id = uuid.UUID(user_id)
            else:
                request.state.user_id = None
                
        except JWTError as exc:
            bound.warning(
                "tenant_auth.invalid_jwt",
                error=str(exc),
                action="reject_401",
            )
            return _build_401(
                request,
                detail="Invalid or expired JWT token.",
            )
        except ValueError:
            bound.warning(
                "tenant_auth.invalid_uuid",
                raw_header=raw_tenant_id,
                action="reject_403",
            )
            return _build_403(
                request,
                detail=(
                    f"Derived tenant ID '{raw_tenant_id}' is not a valid UUID."
                ),
            )

        # ── Stage 4: Database validation query ────────────────────────────────
        try:
            user_uuid = getattr(request.state, "user_id", None)
            session_id = payload.get("session_id") or payload.get("jti")
            session_uuid = uuid.UUID(session_id) if session_id else None
            tenant_row = await _validate_tenant(tenant_uuid, user_uuid, session_uuid)
        except SQLAlchemyError as exc:
            bound.error(
                "tenant_auth.db_error",
                tenant_id=str(tenant_uuid),
                error=str(exc),
                action="reject_500",
                exc_info=True,
            )
            return _build_500(request)
        except Exception as exc:
            bound.error(
                "tenant_auth.db_error",
                tenant_id=str(tenant_uuid),
                error=str(exc),
                action="reject_500",
                exc_info=True,
            )
            return _build_500(request)

        if tenant_row is None:
            bound.warning(
                "tenant_auth.not_found",
                tenant_id=str(tenant_uuid),
                action="reject_403",
                reason="tenant_inactive_or_nonexistent",
            )
            return _build_403(
                request,
                detail=(
                    "The tenant identified by the supplied 'X-Tenant-ID' is "
                    "not registered, inactive, or has been suspended. "
                    "Contact your administrator."
                ),
            )

        _tenant_id, _tenant_slug, _tenant_plan = tenant_row

        # ── Stage 4.5: Check if session is revoked ─────────────────────────────
        if session_uuid:
            async with AsyncSessionLocal() as db_session:
                from app.models.sessions import TenantSession
                from sqlalchemy import select
                stmt = select(TenantSession.is_active).where(TenantSession.id == session_uuid)
                is_active = (await db_session.execute(stmt)).scalar_one_or_none()
                if is_active is False:
                    bound.warning("tenant_auth.session_revoked", action="reject_401")
                    return _build_401(request, detail="Session has been revoked. Please log in again.")
                elif is_active is None:
                    bound.warning("tenant_auth.session_not_found", action="reject_401")
                    return _build_401(request, detail="Invalid session.")

        # ── Stage 5: Bind validated context to request.state ──────────────────
        # request.state is the canonical per-request store (matching the
        # existing request_id pattern in main.py).
        request.state.tenant_id   = _tenant_id
        request.state.tenant_slug = _tenant_slug
        request.state.tenant_plan = _tenant_plan

        # Extend the structlog asyncio-contextvars binding so every log call
        # within the same asyncio task automatically carries tenant context.
        # This cooperates with the existing bound_contextvars block in main.py.
        structlog.contextvars.bind_contextvars(
            tenant_id=str(_tenant_id),
            tenant_slug=_tenant_slug,
        )

        # ── Stage 6: Emit grant telemetry at INFO ─────────────────────────────
        _auth_elapsed_ms = round((time.perf_counter() - _t0) * 1000, 3)
        bound.info(
            "tenant_auth.granted",
            tenant_id=str(_tenant_id),
            tenant_slug=_tenant_slug,
            tenant_plan=_tenant_plan,
            auth_elapsed_ms=_auth_elapsed_ms,
        )

        # ── Stage 7: Call downstream handler ─────────────────────────────────
        response: Response = await call_next(request)

        # Emit total pipeline timing (debug level — high frequency)
        _total_elapsed_ms = round((time.perf_counter() - _t0) * 1000, 3)
        bound.debug(
            "tenant_auth.complete",
            tenant_id=str(_tenant_id),
            status_code=response.status_code,
            total_elapsed_ms=_total_elapsed_ms,
        )

        return response


# =============================================================================
# 5.  FastAPI Dependency — typed tenant_id extraction from request.state
# =============================================================================

async def get_verified_tenant_id(request: Request) -> uuid.UUID:
    """
    FastAPI dependency that extracts the pre-validated ``tenant_id`` from
    ``request.state`` (written by ``TenantAuthMiddleware``).

    Because the middleware has already validated and bound the tenant UUID
    before any route handler runs, this dependency performs **no database
    query** — it simply surfaces the typed UUID from state. If the middleware
    somehow did not run (e.g. during testing with middleware bypassed), it
    raises ``HTTP 401`` as a safe fallback.

    Usage
    -----
    ::

        from app.middleware.tenant_auth import TenantIDDep

        @router.get("/items")
        async def list_items(tenant_id: TenantIDDep) -> ...:
            # tenant_id is a uuid.UUID, guaranteed valid and active
            ...

    Parameters
    ----------
    request:
        Injected by FastAPI — provides access to ``request.state``.

    Returns
    -------
    uuid.UUID
        The validated tenant UUID, ready for CRUD operations.

    Raises
    ------
    HTTPException (401)
        If ``request.state.tenant_id`` is not set (middleware not active).
    """
    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)

    if tenant_id is None:
        # Fallback guard: middleware did not run (test environment or
        # misconfigured middleware stack).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Tenant authentication context is missing. "
                "Ensure TenantAuthMiddleware is registered in the application."
            ),
            headers={"WWW-Authenticate": "TenantID"},
        )

    return tenant_id


# ---------------------------------------------------------------------------
# Typed Annotated alias for concise route signatures
# ---------------------------------------------------------------------------
TenantIDDep = Annotated[uuid.UUID, Depends(get_verified_tenant_id)]
"""
Annotated dependency alias for the verified tenant UUID.

Inject into route handlers as a keyword-only parameter:

    from app.middleware.tenant_auth import TenantIDDep

    async def my_route(tenant_id: TenantIDDep, db: DBDep) -> ...:
        ...

``tenant_id`` will be a ``uuid.UUID`` that has been:
    • Parsed from the ``X-Tenant-ID`` request header.
    • Verified against the active tenant registry in ``public.tenants``.
    • Stored in ``request.state.tenant_id`` by ``TenantAuthMiddleware``.
"""

UserIDDep = Annotated[uuid.UUID | None, Header(alias="X-User-ID")]
"""
Annotated dependency alias for the User UUID from the request header.
Used as a temporary placeholder in Sprint 1 before full JWT middleware is wired.
"""
