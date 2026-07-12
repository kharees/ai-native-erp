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

### Unit-of-work

Sprint 1 moved `crud_finance_core.py` off per-function `db.commit()` onto a
real unit-of-work (CRUD flushes, the route handler owns the single commit,
`get_db()`'s `db_session()` wrapper rolls back automatically on any
exception). That conversion was **not** rolled out further — as of this
sprint, 18 of 25 files in `app/crud/` still call `db.commit()` directly
inside individual functions. A multi-step operation across any of those 18
(e.g. "create invoice, then reserve stock, then post GL" spanning
`universal_invoices.py` + `universal_warehousing.py` + `crud_finance_core.py`)
is **not** atomic — an exception partway through leaves whatever already
committed permanently committed. This matters specifically for AI
tool-calling because an agent chaining multiple tool calls into one logical
action is exactly the multi-step-operation shape that breaks without a real
UoW boundary.

**If you're wiring an agent to call multiple write operations as one
logical unit:** do not assume the existing CRUD functions are safe to
chain and expect all-or-nothing behavior. Either wrap the whole sequence in
your own explicit transaction the way Sprint 1 did for finance-core, or
accept (and design the agent's error-recovery around) partial completion.

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
