# Tenant isolation audit (Sprint 5 #3)

Full audit method: enumerated every SQLAlchemy model with a `tenant_id`
column (100 classes across 32 files), then statically scanned every
`select(`/`update(`/`delete(` call against those models in `app/crud/`,
`app/services/`, `app/api/v1/endpoints/`, and `app/tasks/` for a missing
`tenant_id` filter in the same statement. 18 candidates came out of that
scan; each was manually traced to its caller(s) to determine whether it
was live-exploitable or already protected upstream. Findings below.

## Real cross-tenant vulnerabilities fixed

These were reachable via a normal authenticated HTTP request from one
tenant against another tenant's resource ID — not defense-in-depth,
actual live bugs.

| Where | What was wrong | Fix |
|---|---|---|
| `app/api/v1/endpoints/migration_execution.py` (6 endpoints: execute/pause/resume/cancel/rollback/reconcile) | Computed `tenant_id` from the request but never passed it anywhere. `app/services/migration_execution_engine.py`'s 6 corresponding functions looked up `MigrationSession` by id alone. Any tenant could execute, pause, resume, cancel, **roll back**, or reconcile any other tenant's migration session. | Added `tenant_id` param to all 6 service functions + filtered; threaded it through from the endpoints. |
| `app/api/v1/endpoints/migration_hub.py::validate_migration_session` | Same pattern — `tenant_id` resolved via dependency, never passed to `MigrationEngine.validate_session`. Any tenant could mutate another tenant's mapping/validation state. | Added `tenant_id` param to `validate_session`, filtered, passed through. |
| `app/api/v1/endpoints/migration_hub.py::analyze_cleansing_rules` | No session-ownership check at all before returning record contents (every sibling endpoint in the file — preview, import — already had one). Any tenant could read another tenant's imported row data via the cleansing-duplicates endpoint. | Added the same ownership check used elsewhere in the file. |
| `app/api/v1/endpoints/migration_ai_copilot.py` (3 endpoints: data-quality, cleansing-suggestions, chat) | Same unused-`tenant_id` pattern. Any tenant could read AI-generated data-quality reports, cleansing suggestions, and NL chat answers about another tenant's migration session. | Added `tenant_id` param to all 3 `MigrationAICopilotService` functions, filtered, threaded through. |
| `app/crud/universal_payments.py::create_payment_allocation` | Looked up the target `UniversalPaymentReceipt` via `db.get()` — primary key only, no tenant filter. Any tenant could allocate against another tenant's receipt, decrementing that receipt's `unallocated_amount` and draining that tenant's customer wallet balance. | Replaced with a tenant-scoped `select()`; also added the same filter to the wallet lookups in this function and in `create_payment_receipt`. |

All fixed with regression tests in `tests/test_tenant_isolation.py` — each
test creates a resource as one tenant and confirms a second, independent
tenant (`alt_tenant_headers`) cannot act on it. Each was verified to
actually fail against the pre-fix code before being confirmed green
against the fix (not a tautological test).

## Defense-in-depth added (not independently exploitable today)

| Where | Why it's not live-exploitable now | What was added anyway |
|---|---|---|
| `app/services/erp_connector_engine.py::sync_connector` | Its one caller (`POST /erp-connectors/{id}/sync`) already verifies `connector.tenant_id == tenant_id` before calling in. | Added `tenant_id` param + filter directly in the service function, so a future caller (another endpoint, an agent tool) can't skip the check by mistake. |
| `app/tasks/migration_tasks.py` (Celery worker) | Only ever enqueued server-side by `migration_engine.py::import_session`, itself already tenant-verified before enqueueing. Not reachable from an HTTP request directly. | `run_migration_import` now takes and filters by `tenant_id` too, against a poisoned/replayed queue message. |
| `app/services/ai_intelligence.py::get_inactive_users` | `TenantSession` lookup keyed on `user_id`, but that `user_id` was already sourced from a `UserProfile.tenant_id == tenant_id`-filtered query moments earlier in the same function. | Not changed — already safe via the vetted-id chain; flagged here as reviewed, not a gap. |

## Standardization (audit #5, #6)

9 endpoint files (`erp_connectors.py`, `finance_core.py`, `finance_phase2.py`,
`finance_phase4.py`, `finance_phase5.py`, `finance_reports.py`,
`migration_ai_copilot.py`, `migration_execution.py`, `migration_hub.py`)
each defined their own near-identical local `get_tenant_id(request)`
function — three slightly different implementations, none of them the
canonical one. All 9 replaced with the shared, already-adopted-by-29-other-files
`get_verified_tenant_id` / `TenantIDDep` (`app/middleware/tenant_auth.py`),
which reads the same pre-validated `request.state.tenant_id` the
middleware already sets. Behavior-preserving: confirmed
`TenantAuthMiddleware` always sets that value as a real `uuid.UUID`
(never a string), so the local versions' defensive string-to-UUID
conversion branch was dead code.

## tenant_id null-safety (audit #7)

Already structurally enforced before this sprint: every tenant model's
`tenant_id` column is `nullable=False` at the database level (spot-checked
across `migration.py`, `finance_core.py`, `universal_payments.py` —
consistent everywhere), and no CRUD/service function signature in the
codebase declares `tenant_id` as `Optional` or defaults it to `None`
(verified via a full-codebase grep). No application-layer gap to close
here beyond what the fixes above already do.

## Explicitly not touched

- `app/crud/inventory.py` and `crud_inventory.py` (Sprint 2 #20's flagged
  overlapping legacy inventory implementations) — already correctly
  tenant-scoped in every query checked; left alone per the existing
  decision to not merge/rewrite these without a dedicated sprint.
- `app/services/universal_intelligence.py`, most of `finance_reports.py`,
  `finance_ai_copilot.py` — either fully mocked (no real queries to scope,
  per Sprint 3's explicit AI-feature deferral) or already correctly scoped
  on inspection; no changes needed.
- A pre-existing, unrelated bug was discovered while testing this fix:
  `app/crud/universal_payments.py::create_payment_receipt` raises
  `TypeError` on a customer's very first receipt with `unallocated_amount > 0`
  (`wallet.balance += Decimal(...)` against a freshly-constructed wallet's
  still-`float` balance). Out of scope for a tenant-isolation fix ("do not
  change business logic") — not fixed here, flagged for a follow-up.
