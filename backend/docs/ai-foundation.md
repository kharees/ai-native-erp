# AI Foundation (Sprint 3): scope, what's real now, what's still a gap

Audit findings #26, #27, #28, #38. Explicit instruction for this sprint was
"Only build the AI Foundation" — infrastructure, not features. Forecasting
AI, Document AI, and Analytics AI were explicitly deferred; nothing in this
sprint implements them. This doc is the map of what changed and, just as
important, what a future engineer building an actual feature on top of this
still needs to know before connecting a real agentic copilot to live data.

## What's real now

**AI provider abstraction** (`app/services/ai/`) — `AIProvider` interface,
`OpenAIProvider` / `AnthropicProvider` implementations, `get_ai_provider()`
factory selecting via `AI_PROVIDER` setting. Both SDKs were already declared
in `requirements.txt` and installed but never imported anywhere; this wires
them for real, with tests against mocked SDK clients (no live API key
needed — none is configured in this dev environment; see `OPENAI_API_KEY`
/ `ANTHROPIC_API_KEY` in `.env`). No feature calls this yet — see "Nothing
built on top of the abstraction yet" below.

**Migration duplicate detection** (`app/services/migration_ai_copilot.py`,
audit #26) — replaced a hardcoded `total * 0.05` guess (present in three
separate places, each computing its own inconsistent fake number) with real
fuzzy-matching duplicate detection via the already-existing
`DataCleansingEngine.detect_duplicates` (`app/services/data_cleansing.py`),
the same engine the Cleansing Dashboard endpoint already used. This is
deterministic algorithmic matching, not an LLM call — duplicate detection
doesn't need one, and routing it through the new AI provider abstraction
just to exercise that abstraction would have been scope creep into
"Document AI" territory this sprint excludes.

**Background migration workers** (audit #27) — `app/core/celery_app.py` +
`app/tasks/migration_tasks.py`, a real Celery app on the existing (never-
wired) `REDIS_URL` setting. Sessions above `IMPORT_ASYNC_THRESHOLD` (500
records) now enqueue a task and return immediately instead of running
synchronously inside the HTTP request; the import itself
(`execute_import_chunked` in `app/services/migration_engine.py`) commits
every `CHUNK_SIZE` (200) records instead of once at the end, so a crash or
retry only reprocesses what didn't finish. **Not verified against a live
worker + Redis** — no Redis or Docker was available in the sandbox this was
built in. The dispatch decision, task logic, and chunking/checkpointing are
each verified in isolation (see `tests/test_migration_background.py`), but
"does `celery -A app.core.celery_app worker` actually consume a real queued
task end-to-end" has not been run. Do that once real infrastructure is
available before relying on this for a production-scale import.

## AI tool-calling readiness (audit #38)

Two separate readiness gaps were named. Assessed both; fixed what was safe
to fix at foundation scope, documented the rest.

### Unit-of-work — RESOLVED (Sprint 5 #1)

Sprint 1 moved `crud_finance_core.py` off per-function `db.commit()` onto a
real unit-of-work. Sprint 5 (#1) finished the rollout: all 18 remaining
`app/crud/*.py` files (and the service/endpoint layers calling them) had
their internal `db.commit()` calls removed in favor of `db.flush()`, so the
single commit/rollback boundary is now always `get_db()`'s `db_session()`
wrapper — never an individual CRUD function. A small, deliberately-kept set
of real commits remains for cases that genuinely need cross-connection
visibility before something external happens (enqueuing a Celery task,
claiming an idempotency key against concurrent requests) or must survive an
exception about to be raised — each is commented in place; see
`docs/production-hardening.md`.

**Practical effect for agent tool-calling:** a multi-step operation that
opens exactly one `db_session()` (see `app/services/agent_adapters/` below)
is now genuinely atomic — a failure partway through rolls back everything,
including earlier steps that individually succeeded. `create_and_post_journal_voucher`
in `finance_tools.py` is the concrete example: it used to be two separate,
non-atomic CRUD calls an agent would have had to chain itself; it's now one
tool call, one transaction.

## Agent-safe adapter layer — NEW (Sprint 5 #2, audit #6)

`app/services/agent_adapters/` is the direct answer to audit #6 ("Function
signatures aren't agent-tool-ready — CRUD functions take `db: AsyncSession`
as a parameter, which must never be exposed to an LLM tool schema").

- `base.py` — the `@agent_tool` decorator. Inspects the wrapped function's
  signature *at import time* and raises `AgentToolSignatureError`
  immediately if any parameter is annotated `AsyncSession`/`AsyncConnection`
  or named `db`/`session`/`db_session`/`connection`/`conn`. This is a
  structural guarantee, not a naming convention — a mistake fails app
  startup, not the first agent call that hits it.
- `finance_tools.py`, `inventory_tools.py` — a curated set of adapters
  (`get_account`, `create_account`, `create_and_post_journal_voucher`,
  `get_item`, `create_item`, `execute_stock_movement`) over the existing
  `app/crud` layer, matching the audit's own recommended fix order ("finance
  + billing modules first, since these are the first agent tools planned").
  Each opens its own `db_session()` internally and returns a plain Pydantic
  schema (`from_attributes=True` config, validated while the session is
  still open) — never an ORM object, which would be silently unsafe to
  touch once its session closes.

**What this deliberately does not do:** it does not touch the ~194 other
`AsyncSession`-typed parameters across `app/crud/*.py`. Those functions are
the normal internal application layer — every regular API endpoint depends
on them sharing one request-scoped session for the atomicity Sprint 5 #1
just fixed. Stripping `db` out of CRUD signatures generally (so each
function opened its own session) would directly undo that fix: a
multi-CRUD-call endpoint would go back to being non-atomic. The correct
place to hide the session is at this adapter boundary — built specifically
for whatever eventually calls it as a tool — not the internal layer that
legitimately needs to share a transaction.

**What's still not built:** a tool registry, JSON-schema generation from
these adapters' signatures, or an orchestrator/agent loop (audit #3) — all
explicitly separate, larger, not-yet-scoped work. This is the narrower
precondition: a small set of functions that would actually be safe to
register once that layer exists, plus the automated guard so any future
addition to that set can't accidentally reintroduce a raw session
parameter.

### Service-role Supabase client bypasses RLS

`get_supabase()` (`app/core/database.py`) returns a service-role client
that bypasses Postgres Row-Level Security entirely — by design, for the
Storage/Auth Admin/Realtime operations it exists for. Audited every call
site in `app/` for this sprint: **nothing outside `core/database.py` itself
calls it.** Every business CRUD path already goes through `get_db()` /
`db_session()`, which enforces tenant isolation at the application layer
(every query filters by `tenant_id` explicitly).

So the risk isn't an active leak today — it's structural. Nothing stops a
future feature (including an AI tool) from reaching for `get_supabase()`
out of convenience, at which point tenant safety depends entirely on that
code remembering to filter by `tenant_id` manually, with RLS — the
defense-in-depth layer that would normally catch exactly this class of bug
— unable to help, since it can't see a service-role connection's tenant
context at all.

Fixed by making this impossible to miss: `get_supabase()`'s docstring now
explicitly warns against using it for tenant-scoped business data and
points to `get_db()` as the correct pattern, with a direct note for anyone
building an AI tool-calling agent. This is a documentation/guardrail fix,
not a code-enforced one — a stronger fix (e.g. a wrapper that structurally
prevents tenant-unscoped queries) was judged too large for foundation
scope and would need to intercept an arbitrary Supabase query builder,
which isn't a small addition.

## Nothing built on top of the abstraction yet

Per explicit scope, this sprint does not implement Forecasting AI, Document
AI, or Analytics AI. `universal_intelligence.py`, `finance_ai_copilot.py`,
`ai_intelligence.py`, `finance_reports.py`, and `erp_connector_engine.py`
(the remaining 5 of the 7 services #28 names as mocked) are **unchanged** —
still returning hardcoded/random data. The AI provider abstraction and the
duplicate-detection fix in this sprint are the foundation those features
would build on; building them is separate, future-scoped work.
