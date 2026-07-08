"""
app/core/database.py
====================
Asynchronous database connection layer for the AI-Native ERP platform.

Architecture
------------
  • SQLAlchemy 2.0 async engine backed by asyncpg connection pool.
  • Supabase Python client (service-role) for Storage, Auth Admin, and
    Realtime operations that bypass the asyncpg pool.
  • Named context-manager helpers for unit-of-work transaction patterns.
  • Health-check coroutine consumed by the /health endpoint.
  • All pool parameters are driven by Settings so they can be tuned
    per-environment without code changes.

Usage
-----
  # Inside a FastAPI route (dependency injection):
  async def my_route(db: AsyncSession = Depends(get_db)):
      ...

  # Inside a service / background task (context manager):
  async with db_session() as session:
      result = await session.execute(select(Tenant))
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from supabase import AClient, acreate_client

from app.core.config import settings

log = structlog.get_logger(__name__)


# =============================================================================
# 1.  Declarative ORM Base
# =============================================================================

class Base(DeclarativeBase):
    """
    Shared declarative base for all SQLAlchemy ORM models.

    All model classes MUST inherit from this Base to participate in
    Alembic auto-generation and the async engine session factory.
    """
    pass


# =============================================================================
# 2.  Async Engine — singleton, created once at import time
# =============================================================================

def _build_engine() -> AsyncEngine:
    """
    Construct a configured AsyncEngine with asyncpg pool tuning.

    Pool parameters are read from Settings so they can differ between
    development (small pool) and production (larger pool).

    asyncpg pool semantics:
      pool_size      — number of persistent connections kept alive
      max_overflow   — extra connections allowed beyond pool_size under load
      pool_timeout   — seconds to wait for a connection before raising
      pool_recycle   — seconds before a connection is proactively replaced
                       (prevents silent drops from load-balancer timeouts)
      pool_pre_ping  — issues a cheap SELECT 1 before handing out a
                       connection; discards and replaces stale connections
    """
    connect_args: dict = {
        # asyncpg specific — use prepared-statement caching
        "statement_cache_size": 100,
        # Server-side connection timeout (seconds)
        "command_timeout": 60,
        # Application name visible in pg_stat_activity
        "server_settings": {
            "application_name": settings.APP_NAME,
            # Enforce tenant isolation at session level when using Supabase RLS
            "search_path": "public",
        },
    }

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,                        # SQL logging in dev
        echo_pool=settings.DEBUG,                   # pool event logging in dev
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        connect_args=connect_args,
        # Use NullPool for serverless / Lambda environments where
        # persistent connections are not reused across invocations.
        # poolclass=NullPool,
    )

    # Attach pool event listeners for observability
    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection, connection_record):
        log.debug("db_pool_connect", pid=id(dbapi_connection))

    @event.listens_for(engine.sync_engine, "checkout")
    def _on_checkout(dbapi_connection, connection_record, connection_proxy):
        log.debug("db_pool_checkout", pid=id(dbapi_connection))

    return engine


engine: AsyncEngine = _build_engine()


# =============================================================================
# 3.  Async Session Factory
# =============================================================================

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # don't lazy-load after commit in async contexts
    autoflush=False,          # explicit flush gives predictable SQL ordering
    autocommit=False,
)


# =============================================================================
# 4.  Supabase Async Client — singleton managed by lifespan
# =============================================================================

_supabase_client: AClient | None = None


def get_supabase() -> AClient:
    """
    Return the singleton Supabase async client.

    Raises RuntimeError if called before init_db() has completed
    (i.e., before the FastAPI lifespan startup has run).
    """
    if _supabase_client is None:
        raise RuntimeError(
            "Supabase client is not initialised. "
            "Ensure init_db() is called during application startup."
        )
    return _supabase_client


# =============================================================================
# 5.  Lifespan Hooks — called by FastAPI application lifespan
# =============================================================================

async def init_db() -> None:
    """
    Initialise all database resources on application startup.

    Actions:
      1. Eagerly warm-up the asyncpg connection pool by opening and
         releasing ``DB_POOL_SIZE`` connections.
      2. Create the Supabase async client with the service-role key
         (bypasses Row-Level Security — use only in backend code).
      3. Emit a structured log confirming pool readiness.
    """
    global _supabase_client

    t0 = time.perf_counter()

    # --- Warm up asyncpg pool -----------------------------------------------
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        log.info(
            "db_pool_ready",
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
    except OperationalError as exc:
        log.error("db_pool_init_failed", error=str(exc))
        raise

    # --- Supabase client ----------------------------------------------------
    _supabase_client = await acreate_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )
    log.info("supabase_client_ready", url=settings.SUPABASE_URL)


async def close_db() -> None:
    """
    Gracefully release all database resources on application shutdown.

    Disposes the asyncpg connection pool so Postgres sees clean
    disconnects rather than abrupt TCP closes.
    """
    await engine.dispose()
    log.info("db_pool_disposed")


# =============================================================================
# 6.  Connection / Session Context Managers
# =============================================================================

@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager yielding a managed AsyncSession.

    Usage (outside FastAPI dependency injection)::

        async with db_session() as session:
            result = await session.execute(select(Tenant).where(...))
            tenants = result.scalars().all()

    Behaviour:
      • Commits on clean exit.
      • Rolls back and re-raises on any exception.
      • Always closes the session on exit (returns connection to pool).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            log.error("db_session_rollback", error=str(exc))
            raise
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def db_transaction() -> AsyncGenerator[AsyncConnection, None]:
    """
    Async context manager yielding a raw AsyncConnection in an explicit
    transaction block.

    Prefer this for DDL operations or multi-statement scripts that must
    not be split across multiple sessions.

    Usage::

        async with db_transaction() as conn:
            await conn.execute(text("CREATE TABLE ..."))
    """
    async with engine.begin() as conn:
        yield conn


# =============================================================================
# 7.  FastAPI Dependency — injected into route handlers
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a per-request AsyncSession.

    Follows the unit-of-work pattern:
      • A new session is opened at the start of each request.
      • Committed on success, rolled back on exception.
      • Returned to the asyncpg pool when the response is sent.

    Inject with::

        from fastapi import Depends
        from app.core.database import get_db

        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with db_session() as session:
        yield session


# =============================================================================
# 8.  Health Check Helper
# =============================================================================

async def check_db_health() -> dict:
    """
    Verify database connectivity. Used by the /health endpoint.

    Returns a dict with status, latency_ms, and pool stats suitable
    for inclusion in a health-check JSON response.
    """
    t0 = time.perf_counter()
    try:
        async with engine.connect() as conn:
            row = await conn.execute(
                text("SELECT current_database(), version()")
            )
            db_name, pg_version = row.one()

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        pool = engine.pool  # type: ignore[attr-defined]

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "database": db_name,
            "postgres_version": pg_version.split(" ")[0],
            "pool": {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            },
        }
    except Exception as exc:
        log.error("db_health_check_failed", error=str(exc))
        return {
            "status": "unhealthy",
            "error": str(exc),
        }
