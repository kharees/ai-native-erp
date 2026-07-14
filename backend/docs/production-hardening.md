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

## GST/tax calculation is absent system-wide, not just in the agent layer

**Priority: higher than the two items below it, and separate from them.**
This is a whole-system compliance gap discovered while scoping
`app/agent/tools/billing_tools.py`'s `create_invoice` tool — it is not an
agent-layer problem and fixing the agent layer does not fix it.

`crud.universal_invoices.create_tax_invoice` is a pure pass-through: every
tax figure (`cgst_amount`/`sgst_amount`/`igst_amount` per line item,
`total_cgst`/`total_sgst`/`total_igst`/`tds_amount` on the invoice) is
persisted exactly as submitted, with zero calculation, zero validation
that line-item tax sums reconcile with invoice totals, and zero lookup
against `UniversalTaxConfiguration`/`UniversalHSNSAC`
(`app/crud/universal_taxes.py`) — real tables holding tenant-configured
tax rates and HSN/SAC codes that **nothing in the codebase ever queries**.
A human calling `POST /omnichannel-billing/invoices/tax` directly today
must pre-compute every tax number by hand; the API provides no safety net.

**Consequence for the agent tool:** `create_invoice`'s input schema
deliberately excludes all seven tax-amount fields for v1 (see the comment
above `create_invoice` in `billing_tools.py`) — the tool can only create
non-tax / zero-tax invoices until this is fixed. This is a narrower, safer
symptom of the underlying gap, not a fix for it: the gap exists for every
other caller (the UI, direct API access, any future tool) regardless of
what this one tool's schema allows.

**Real fix, tracked as its own backlog item, not bundled into any agent
work:** a tax-calculation service that resolves the correct rate from
`UniversalTaxConfiguration`/`UniversalHSNSAC` given each line item's HSN/SAC
code and the tenant's jurisdiction, computes CGST+SGST (intra-state) vs
IGST (inter-state) correctly, and is called from `create_tax_invoice`
(and any other invoice-creation path) rather than trusting caller-supplied
numbers. That's real, dedicated compliance work — not something to fold
into an unrelated task's scope.

## Agent billing tools — no idempotency protection yet (money-mutating)

**Priority: must be fixed before the orchestrator goes live** — this is
not a "someday" item like most of this doc; it blocks connecting an LLM
to real money-moving operations.

`app/agent/tools/billing_tools.py`'s `create_invoice` and `record_payment`
handlers wrap `crud.universal_invoices.create_tax_invoice` and
`crud.universal_payments.create_payment_receipt` directly, with no
idempotency-key claim/check around them — unlike their HTTP-endpoint
counterparts (`app/api/v1/endpoints/universal_invoices.py`,
`universal_payments.py`), which both wrap the same CRUD calls in
`claim_idempotency_key`/`complete_idempotency_key`
(`app/services/idempotency.py`).

This was a deliberate scoping decision, not an oversight: generating or
supplying the idempotency key is properly an *orchestrator* concern (e.g.
derived deterministically from a conversation turn ID so a retried tool
call after an ambiguous failure doesn't double-create), and no
orchestrator exists yet (audit #3 — still true as of this entry). Each
handler has an inline `# TODO` marking this explicitly.

**The concrete risk:** an LLM agent retrying a tool call it believes
failed (timeout, ambiguous error, its own confusion about whether the
call completed) can create a duplicate invoice or double-record a
payment, with no protection at all today. Before wiring any orchestrator
to these two handlers specifically, thread the same
`claim_idempotency_key`/`complete_idempotency_key` pattern through them,
with the orchestrator supplying a real, stable key per logical tool
invocation.

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
