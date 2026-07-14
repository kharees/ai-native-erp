"""
app/core/rate_limit.py
=======================
Shared slowapi Limiter instance for per-endpoint rate limiting (brute-force
protection on /auth/login — see app/api/v1/endpoints/auth.py).

Storage: in-memory (slowapi/`limits`' default MemoryStorage). Correct for
a single-process run; each `uvicorn --workers N` process gets its own
independent counter, so a production deployment with multiple workers
needs a shared store to make the limit global rather than per-worker —
e.g. `Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)`,
reusing the same Redis instance Celery already talks to
(app/core/celery_app.py). Not wired to Redis here because this sandbox
has no reachable Redis instance to verify it against live (the same
constraint already noted for Celery in docs/ai-foundation.md).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
