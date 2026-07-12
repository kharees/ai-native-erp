"""
app/tasks/migration_tasks.py
==============================
Celery task wrapping the chunked migration import (app/services/
migration_engine.py:execute_import_chunked). Triggered by
MigrationEngine.import_session() for sessions above IMPORT_ASYNC_THRESHOLD
records instead of running inline in the HTTP request.

Celery tasks are sync by default; the import logic is async (it's built on
SQLAlchemy's async session), so this opens its own event loop and its own
DB session per run — it executes in a separate worker process from the
request that enqueued it, so it cannot reuse the request's session.
"""

import asyncio
import uuid

import structlog
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.migration import MigrationSession

log = structlog.get_logger(__name__)


async def _run_import(session_id: str) -> None:
    from app.services.migration_engine import execute_import_chunked

    async with AsyncSessionLocal() as db:
        stmt = select(MigrationSession).where(MigrationSession.id == uuid.UUID(session_id))
        session = (await db.execute(stmt)).scalar_one_or_none()
        if session is None:
            log.error("migration_import_task.session_not_found", session_id=session_id)
            return
        await execute_import_chunked(db, session)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, name="migration.run_import")
def run_migration_import(self, session_id: str) -> None:
    """
    Runs the full chunked import for `session_id` in a worker process.

    Retry semantics: execute_import_chunked commits after every chunk
    (CHUNK_SIZE records), each marking is_imported=True on success — so if
    this task dies mid-run (worker crash, DB blip) and Celery retries it,
    the record query inside execute_import_chunked (is_imported == False)
    naturally skips everything already committed and only reprocesses the
    remainder. A retry is a resume, not a restart.
    """
    log.info("migration_import_task.started", session_id=session_id, attempt=self.request.retries + 1)
    try:
        asyncio.run(_run_import(session_id))
        log.info("migration_import_task.completed", session_id=session_id)
    except Exception as exc:
        log.error(
            "migration_import_task.failed",
            session_id=session_id,
            attempt=self.request.retries + 1,
            error=str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc)
