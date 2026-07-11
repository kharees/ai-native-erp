"""
AI-Native ERP — FastAPI Application Entry Point
=================================================
Multi-tenant asynchronous API server.

Startup order
-------------
  1. lifespan() fires → init_db() warms the asyncpg pool and Supabase client.
  2. Middleware stack is applied (CORS → TrustedHost → request-id logging).
  3. Routers are mounted under /api/v1.
  4. Health endpoints are available immediately at / and /health.

Usage
-----
    # Development (hot-reload)
    uvicorn main:app --reload --port 8000

    # Production (multi-worker)
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import check_db_health, close_db, init_db

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
log = structlog.get_logger(__name__)


# ===========================================================================
# Response Schemas (Pydantic)
# ===========================================================================

class RootResponse(BaseModel):
    """Response body for the root GET / endpoint."""
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Semver version string")
    environment: str = Field(..., description="Runtime environment label")
    status: str = Field(..., description="Operational status")
    docs_url: str | None = Field(None, description="Interactive docs URL (None in production)")


class DatabaseHealthDetail(BaseModel):
    """Postgres-specific health metrics returned inside HealthResponse."""
    status: str
    latency_ms: float | None = None
    database: str | None = None
    postgres_version: str | None = None
    pool: dict[str, int] | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """
    Full health-check response body.

    Consumed by:
      • Kubernetes liveness / readiness probes  →  GET /health
      • Load-balancer health checks             →  GET /health
      • Deep diagnostic endpoint               →  GET /health/detailed
    """
    status: str = Field(..., description="'healthy' | 'degraded' | 'unhealthy'")
    environment: str
    version: str
    request_id: str
    uptime_seconds: float | None = None
    database: DatabaseHealthDetail | None = None


# ---------------------------------------------------------------------------
# Application start time (for uptime calculation)
# ---------------------------------------------------------------------------
_app_start: float = 0.0


# ===========================================================================
# Lifespan — startup / shutdown
# ===========================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage database connections and background services for the app lifetime.

    Startup:
      • Warms the asyncpg connection pool with a probe query.
      • Creates the Supabase async client singleton.
      • Records the application start timestamp.

    Shutdown:
      • Disposes the asyncpg pool (clean Postgres disconnects).
    """
    global _app_start
    _app_start = time.perf_counter()

    log.info(
        "app_startup",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.ENVIRONMENT,
    )

    await init_db()
    log.info("app_ready")

    yield  # ← application runs here

    log.info("app_shutdown")
    await close_db()


# ===========================================================================
# FastAPI Application
# ===========================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**AI-Native ERP** — multi-tenant REST API.\n\n"
        "All endpoints under `/api/v1` require a valid Supabase JWT "
        "(`Authorization: Bearer <token>`) unless documented otherwise."
    ),
    # Disable interactive docs in production (security best practice)
    docs_url="/api/docs"        if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc"      if settings.ENVIRONMENT != "production" else None,
    openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)


# ===========================================================================
# Middleware Stack
# ===========================================================================

# 1. CORS — must be first so pre-flight OPTIONS requests are handled before
#    any business-logic middleware runs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# 2. Trusted Host — rejects requests with unexpected Host headers.
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# 3. Tenant Authentication & Route Protection — validates X-Tenant-ID header
#    on every protected API request, binds tenant context to request.state,
#    and extends structlog contextvars for automatic per-request telemetry.
#    Must be registered after CORS / TrustedHost so those layers run first.
#    Health probes (/health, /), OpenAPI docs, and OPTIONS requests bypass this.
from app.middleware.tenant_auth import TenantAuthMiddleware  # noqa: E402

app.add_middleware(TenantAuthMiddleware)


# ===========================================================================
# Request Logging Middleware
# ===========================================================================

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    """
    Attach a unique X-Request-ID to every request and log timing + status.

    The request_id propagates into structured log fields for every log call
    that happens within the same asyncio task, enabling distributed tracing
    without a dedicated tracer sidecar.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    t0 = time.perf_counter()

    with structlog.contextvars.bound_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    ):
        log.info("request_received")
        response: Response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        log.info(
            "request_completed",
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

    response.headers["X-Request-ID"] = request_id
    return response


# ===========================================================================
# Global Exception Handlers
# ===========================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — returns a safe 500 response."""
    request_id = getattr(request.state, "request_id", "unknown")
    log.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "request_id": request_id,
        },
    )


# ===========================================================================
# Root & Health Endpoints
# ===========================================================================

@app.get(
    "/",
    response_model=RootResponse,
    tags=["System"],
    summary="API root — confirms the service is reachable",
)
async def root() -> RootResponse:
    """
    Lightweight liveness check.
    Returns application identity metadata without touching the database.
    """
    return RootResponse(
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        status="operational",
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Shallow health check — Kubernetes liveness probe",
)
async def health_check(request: Request) -> HealthResponse:
    """
    **Shallow health check** — does NOT probe the database.

    Use this endpoint for Kubernetes **liveness probes** where a fast
    response (< 5 ms) is needed. Returns 200 as long as the process is alive.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    uptime = round(time.perf_counter() - _app_start, 2) if _app_start else None

    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
        request_id=request_id,
        uptime_seconds=uptime,
    )


@app.get(
    "/health/detailed",
    response_model=HealthResponse,
    tags=["System"],
    summary="Deep health check — database connectivity + pool stats",
)
async def health_check_detailed(request: Request) -> HealthResponse:
    """
    **Deep health check** — probes the Postgres database and returns pool metrics.

    Use this endpoint for Kubernetes **readiness probes** (the pod should only
    receive traffic once the DB connection pool is ready) and for ops dashboards.

    Response fields:
    - `database.status` — `healthy` | `unhealthy`
    - `database.latency_ms` — round-trip time for `SELECT current_database()`
    - `database.pool` — asyncpg pool stats (size, checked_in, checked_out, overflow)
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    uptime = round(time.perf_counter() - _app_start, 2) if _app_start else None

    db_health_raw: dict[str, Any] = await check_db_health()
    db_detail = DatabaseHealthDetail(**db_health_raw)

    overall_status = "healthy" if db_detail.status == "healthy" else "unhealthy"

    return JSONResponse(
        status_code=(
            status.HTTP_200_OK
            if overall_status == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        content=HealthResponse(
            status=overall_status,
            environment=settings.ENVIRONMENT,
            version=settings.APP_VERSION,
            request_id=request_id,
            uptime_seconds=uptime,
            database=db_detail,
        ).model_dump(),
    )


# ===========================================================================
# API v1 Router Registration
# ===========================================================================
# Uncomment each router as the corresponding module is created.
# All routers are mounted under /api/v1 with a consistent tag convention.
# ---------------------------------------------------------------------------

from app.api.v1.router import api_router

app.include_router(api_router, prefix="/api/v1")

# NOTE: The auth router is already mounted at /api/v1/auth via api_router
# (see app/api/v1/router.py: api_router.include_router(auth.router, prefix="/auth", ...)).
# A duplicate explicit mount used to exist here — removed to avoid two live
# copies of the same routes in the OpenAPI schema and app.routes.
