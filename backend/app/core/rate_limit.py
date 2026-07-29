"""
app/core/rate_limit.py
=======================
Shared slowapi Limiter instance for per-endpoint rate limiting (brute-force
protection on /auth/login — see app/api/v1/endpoints/auth.py — and,
per-user throttling on the AI chat and order-capture upload endpoints —
see app/api/v1/endpoints/agent_chat.py and order_capture.py).

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
from starlette.requests import Request

limiter = Limiter(key_func=get_remote_address)


def user_or_ip_key(request: Request) -> str:
    """Per-endpoint slowapi key_func: keys the limit on the authenticated
    user_id (app.middleware.tenant_auth.TenantAuthMiddleware writes the
    JWT-verified user_id to request.state before any route/rate-limit
    check runs — see get_verified_user_id's docstring), falling back to
    the caller's IP for unauthenticated requests. Prefixed so a
    user-keyed bucket can never collide with an IP-keyed one (a user_id
    UUID and an IP string are already disjoint in practice, but the
    prefix makes that guarantee explicit rather than incidental)."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"
