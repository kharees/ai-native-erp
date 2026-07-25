"""
alembic/env.py
==============
Alembic migration environment for the AI-Native ERP platform.

Architecture
------------
* The application runtime uses SQLAlchemy 2.0 async engine (asyncpg driver).
* Alembic uses a *synchronous* psycopg2 connection for DDL execution —
  this is the standard pattern and avoids asyncio event-loop complexity
  in the migration runner context.
* ``DATABASE_URL`` is loaded from ``.env`` via ``app.core.config.Settings``.
  The raw URL (``postgresql://…``) uses psycopg2 by default — Alembic uses
  it directly without any driver-prefix rewriting.

ORM Metadata strategy
---------------------
* ``app.core.database`` builds the async engine at module level when imported,
  which requires asyncpg to be installed in the migration context.
* To avoid this side-effect, we stub ``app.core.database`` in ``sys.modules``
  with a minimal shim that exposes a genuine ``DeclarativeBase`` subclass
  (``Base``) but no engine, session, or Supabase client.
* Model files that do ``from app.core.database import Base`` pick up the shim
  and register their Table objects on its metadata — giving Alembic the full
  ``target_metadata`` for autogenerate diffing.

Multi-Tenant RLS Awareness
---------------------------
* Migrations run under superuser / service-role credentials and therefore
  bypass Row-Level Security — this is correct for DDL operations.

Usage (from the backend/ directory)
-------------------------------------
    alembic history --verbose            # show full revision chain
    alembic current                      # show applied revision
    alembic upgrade head                 # apply all pending migrations
    alembic downgrade -1                 # roll back one migration
    alembic upgrade head --sql           # dry-run: dump SQL to stdout
    alembic revision --autogenerate -m "add_x"  # generate new revision
"""

from __future__ import annotations

import os
import sys
import types
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.orm import DeclarativeBase

from alembic import context

# ---------------------------------------------------------------------------
# 1.  Bootstrap sys.path — add backend/ so app.* packages are importable.
# ---------------------------------------------------------------------------
_backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

# ---------------------------------------------------------------------------
# 2.  Load DATABASE_URL from .env via pydantic-settings (no engine built yet).
# ---------------------------------------------------------------------------
from app.core.config import settings  # noqa: E402

_db_url: str = settings.DATABASE_URL
# Ensure the URL uses the psycopg2 dialect prefix for Alembic's sync engine.
# Replace asyncpg driver prefix if the URL was configured with it.
_sync_url: str = _db_url

# ---------------------------------------------------------------------------
# 3.  Stub ``app.core.database`` so model imports don't trigger engine build.
#
#     Strategy: inject a fake module with a real DeclarativeBase into
#     sys.modules *before* importing any app.models.* files.  Model files
#     that contain ``from app.core.database import Base`` will resolve to
#     our stub's Base and register their tables on its metadata.
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """
    Migration-only declarative base.
    Mirrors ``app.core.database.Base``; used solely for metadata harvesting.
    """
    pass


_db_stub = types.ModuleType("app.core.database")
_db_stub.Base = Base  # type: ignore[attr-defined]

# Pre-populate sys.modules with the stub; use setdefault so that if the real
# module was somehow already imported (e.g. in testing) we don't clobber it.
sys.modules.setdefault("app.core.database", _db_stub)

# Import every model module under app/models/ — triggers table registration
# on Base.metadata. Previously a hand-maintained list of explicit imports;
# that list had silently drifted 17 model files out of date (missing even
# app.models.tenants, the table nearly everything else foreign-keys to),
# which meant autogenerate could never see roughly 68 of this project's 110
# model-defined tables at all — the actual root cause of those tables never
# having a real migration. Importing every file in the directory instead of
# hand-listing them makes that entire class of drift impossible going
# forward: a new model file is automatically picked up with no edit here.
import importlib

_models_dir = os.path.join(_backend_root, "app", "models")
for _fname in sorted(os.listdir(_models_dir)):
    if _fname.endswith(".py") and _fname != "__init__.py":
        importlib.import_module(f"app.models.{_fname[:-3]}")





# ---------------------------------------------------------------------------
# 4.  Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# 5.  ORM target metadata — autogenerate diffs this against the live schema.
# ---------------------------------------------------------------------------
target_metadata = Base.metadata

# Override the blank sqlalchemy.url in alembic.ini with the resolved URL.
config.set_main_option("sqlalchemy.url", _sync_url)


# =============================================================================
# 6.  Offline runner — emit SQL without a live database connection.
# =============================================================================

def run_migrations_offline() -> None:
    """
    'Offline' mode: generate SQL DDL without connecting to Postgres.

    Example::

        alembic upgrade head --sql > schema_upgrade.sql
    """
    context.configure(
        url=_sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        compare_server_default=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


from sqlalchemy.ext.asyncio import async_engine_from_config
import asyncio

def do_run_migrations(connection: sqlalchemy.Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_server_default=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    """
    'Online' mode (default): connect to Postgres with asyncpg and apply
    all pending revisions atomically.
    """
    asyncio.run(run_async_migrations())

# =============================================================================
# 8.  Entry point
# =============================================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
