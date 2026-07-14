# Production hardening: Sprint 4 residual gaps

Consolidates every "documented, not attempted" pointer made throughout
Sprint 4 in one place, plus the full write-up for audit #13
(BaseHTTPMiddleware). Each item below was deliberately scoped down —
either because the full fix is materially larger/riskier than the rest of
this sprint's changes, or because it couldn't be verified in the sandbox
this work was done in (no Docker, no Redis, no CI runner). None of these
are silent gaps; each is cross-referenced from the commit/code that found it.

## #13 — TenantAuthMiddleware is BaseHTTPMiddleware, not pure ASGI

**What's real now:** `middleware/tenant_auth.py`'s own short-circuited
401/403/500 responses (returned directly, before `call_next()` ever runs)
never passed back through `CORSMiddleware`'s ASGI `send`-wrapping — a
concrete, live bug this sprint found while testing #10's silent-refresh
flow: an expired access token produced a response Chrome reported as a
CORS failure, masking the real 401. Patched with `_add_cors_headers()`,
manually attaching `Access-Control-Allow-Origin`/`-Credentials` to those
three responses.

**What's not fixed:** that patch is targeted at the one gap this sprint
could concretely observe. The underlying cause — `BaseHTTPMiddleware`
bridges the ASGI `send`/`receive` protocol into a `Request`/`Response`
abstraction in a way Starlette's own docs warn interacts poorly with other
ASGI middleware and streaming responses — remains. The full fix is
converting `TenantAuthMiddleware` to pure ASGI middleware (implementing
`__call__(scope, receive, send)` directly) or a FastAPI dependency instead
of a `BaseHTTPMiddleware` subclass. That's a rewrite of the security-
critical auth hot path that runs on 100% of traffic — not something to
attempt without dedicated time to re-verify every one of the ~100 backend
tests plus live-testing every auth/session/RBAC edge case again, given how
much of Sprints 1-4 went into getting that path correct in the first place.

## #13b — request_logging_middleware also has the BaseHTTPMiddleware exception-propagation gap

**Priority: higher than #13 — fix this one first.** #13 masks a header on
an already-produced auth error response (annoying, but the 401 itself
still reaches the client). #13b can prevent the client from receiving
*any* usable error response at all when a route raises unexpectedly —
that's every route, not just auth, and it's the difference between a
client seeing a clean error and seeing nothing/a connection failure.

**Newly found** (while writing `tests/test_universal_intelligence.py`'s
"AI provider unconfigured" test): `main.py`'s `request_logging_middleware`
(registered via `@app.middleware("http")`, which Starlette implements as
`BaseHTTPMiddleware` under the hood — same mechanism as #13's
`TenantAuthMiddleware`) has a *different* symptom of the same root cause.
An unhandled exception raised inside a route (e.g.
`AIProviderNotConfiguredError` propagating out of
`universal_intelligence.py` when no AI provider is configured) does reach
`main.py`'s `global_exception_handler` — confirmed via its log line
actually firing — but the resulting `JSONResponse` cannot pass back
through this middleware, so instead of a clean 500 response reaching the
client, the raw exception propagates further up the ASGI stack. Under
httpx's `ASGITransport` (i.e. every test in this suite) that means it
surfaces as a raised Python exception at the test-client call site
instead of an HTTP response; the equivalent behavior in an actual
deployed server (uvicorn, not the test transport) would need separate
verification, since production-server exception handling doesn't
necessarily fail the same way.

**Not fixed here** — found and worked around inside one test
(`test_ai_dashboard_raises_instead_of_fabricating_when_ai_unconfigured`
asserts via `pytest.raises` instead of a status code), not fixed at the
source, since the real fix is the same pure-ASGI rewrite #13 already
scoped out as too large to attempt without dedicated time. Distinct
backlog item from #13 though: different middleware, different symptom
(response-delivery failure vs. missing headers), so fixing #13 alone
would not fix this. Worth prioritizing over #13 if forced to pick one —
a swallowed/misdelivered error response on unhandled exceptions is a
correctness gap on every route, not just the auth path.

## Docker / docker-compose / CI — unverified against live infrastructure

`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, and
`.github/workflows/ci.yml` (Sprint 4 #34) were written correctly against
the project's actual dependencies and verified indirectly — every command
each file runs (`pip install -r requirements.txt`, `npm run build`,
`pytest`) was run for real locally, including the exact CI-style env-var
set with no `.env` file present. What was **not** run: an actual
`docker build`, `docker compose up`, or GitHub Actions workflow — no
Docker daemon or CI runner was available in the sandbox. Before relying on
these for a real deployment, run them for real at least once.

## Celery / Redis — live worker unverified

`app/core/celery_app.py` and `app/tasks/migration_tasks.py` (Sprint 3 #27)
are real, tested in isolation (task dispatch logic, chunked/checkpointed
import logic), but no Redis instance was available in this sandbox to
verify an actual `celery -A app.core.celery_app worker` process consuming
a real queued task end-to-end. Do that once real infrastructure is available.

## Transactional outbox — write side only, no relay/dispatcher

`app/services/outbox.py` (Sprint 4 #37) reliably writes events in the same
transaction as the business change they describe — that part is real and
tested. Nothing reads `outbox_events` rows and actually publishes them
(webhook, Celery task, message broker). Building that relay is separate,
larger infrastructure: it needs its own polling/locking strategy (to
avoid two relay instances double-publishing the same row), retry/backoff
for downstream delivery failures, and a decision about at-least-once vs
exactly-once semantics for whatever's consuming these events.

## RBAC in-process cache — not multi-instance-safe

`middleware/rbac.py`'s 30s TTL cache (Sprint 4 #7) is real and reduces DB
load, but it's per-process. Running multiple app workers/replicas means
each has its own cache; revoking a role on one worker doesn't invalidate
another worker's still-cached "allowed" result until its entry naturally
expires (worst case: 30s window). A correct multi-instance version needs
a shared store (Redis, already wired for Celery) with explicit
invalidation on every RBAC-mutating endpoint — a larger change touching
every role/permission write path, not done here.

## Optimistic locking — Account only, not invoices/orders

Sprint 4 #36 added a `version` column + `expected_version` check to
`Account` (Chart of Accounts) as the concrete implementation of this
pattern. The audit's named examples — invoices, orders — don't currently
have real update (`PATCH`) endpoints to protect (journal vouchers are
immutable once posted by design, per Sprint 1). If/when update endpoints
are added for invoices or orders, the same pattern (version column +
optional `expected_version` field on the Update schema) applies directly.

## Tenant plan enforcement — one quota, not a framework

Sprint 4 #35 enforces `max_users` per plan at user-provisioning time as
the concrete proof the mechanism works — not a general feature-flag or
quota framework nothing else calls yet. See `app/core/plans.py` for how
to add more quotas (storage, API rate, module access): a new field on
`PlanLimits` and a check at whichever creation/action endpoint it applies
to.

## Test suite — event_loop fixture architecture

Sprint 4 #29 fixed the concrete stale-import bug this sprint's own new
code (`app/tasks/migration_tasks.py`) introduced, and made the test
database URL actually configurable via `DATABASE_URL`. The deprecated
session-scoped `event_loop` fixture in `tests/conftest.py` was
deliberately left as-is: the module-level `engine`/connection pool it
works around is bound to whichever event loop existed when it was
created, so pytest-asyncio's modern per-test-function event loop default
would orphan that pool after the first test. The real fix — engine
creation per test function instead of module level — means restructuring
`db_session`, `async_client`, and every fixture built on them, which
isn't safe to change without re-verifying all ~100 tests individually.

## Access token still in localStorage

Sprint 4 #10 moved the refresh token to an httpOnly cookie (the higher-
value half of the fix — it's long-lived and the more damaging thing to
leak). The access token itself still persists to `localStorage` via
Zustand — fully memory-only storage means bootstrapping a fresh access
token via a silent `/refresh` call on every app load before rendering
protected content, a real change to the auth bootstrap flow (session
hydration was already a hard-won fix earlier in this project) that
deserves dedicated verification rather than being bundled into the
cookie change.
