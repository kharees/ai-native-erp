"""
app/core/celery_app.py
========================
Celery application instance, backed by Redis (already declared in
requirements.txt/config — REDIS_URL — but never wired to anything until
this sprint; the only prior reference in the codebase was a comment:
"In a real app, you'd trigger a Celery task here.").

Running a worker
-----------------
    celery -A app.core.celery_app worker --loglevel=info

Requires a reachable Redis instance at settings.REDIS_URL for both the
broker and result backend.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ai_native_erp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.migration_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # A task that raises is retried by the tasks themselves (see
    # app/tasks/migration_tasks.py) rather than acked-and-dropped.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
