# Inventory: three coexisting implementations

Audit finding #20. This document is the concrete "assessment and
documentation" deliverable for that finding — a safe, additive fix. Merging
or deleting any of these three live, separately-wired API surfaces was
judged too high-risk for this sprint (each is mounted, tested, and — for
Universal Inventory and the Handloom Saree engine — actively used by real
frontend pages); this doc instead makes the duplication legible so future
work builds on the canonical one instead of a fourth parallel system.

## The three systems

| # | Mount | Router file | CRUD file | Model / table |
|---|---|---|---|---|
| 1 | `/api/v1/inventory` | `app/api/v1/inventory.py` | `app/crud/inventory.py` | `InventoryItem` / `inventory_items` |
| 2 | `/api/v1/inventory/saree` | `app/api/v1/endpoints/inventory.py` | `app/crud/crud_inventory.py` | `InventoryItem` / `inventory_items` (**same table as #1**) |
| 3 | `/api/v1/universal-inventory` | `app/api/v1/endpoints/universal_inventory.py` | `app/crud/universal_inventory.py` | `UniversalItemMaster` / `universal_item_master` |

## The sharper problem: #1 and #2 aren't just parallel, they collide

This is worse than three independent systems that happen to solve the same
problem differently. #1 ("general ERP inventory", Phase 1/2) and #2 ("Handloom
Saree" engine) are two **completely independent routers and CRUD modules
that both read and write the exact same `inventory_items` table** —
`app/crud/inventory.py` and `app/crud/crud_inventory.py` each implement
their own validation, duplicate-SKU checks, and update logic against
`InventoryItem` with zero coordination between them. A bug fix, a new
validation rule, or (as of Sprint 1) an RBAC check applied to one has no
effect on the other, on the same rows.

Confirmed while writing this doc: `app/api/v1/inventory.py` (#1) has **no
RBAC** (`RequirePermission`) on any route — the same class of gap Sprint 1
fixed on `app/api/v1/endpoints/inventory.py` (#2), which sits outside
`app/api/v1/endpoints/*`, the path the original audit finding for RBAC (#5)
scoped itself to, so it was missed. Flagged here as a follow-up; not fixed
in this sprint (out of the explicit Sprint 2 issue list).

## Universal Inventory (#3) is canonical

`/universal-inventory` is the actively developed, actively wired suite:
Items, Categories, Brands, UOM, Warehouses, Bins, Stock movements, Ledger,
Tracking (batches/serials), Reports, and Intelligence all live here, and
every corresponding frontend page (`frontend/src/app/(main)/universal-inventory/**`)
calls this API. It should be treated as the system of record for inventory
going forward. #1 and #2 should not gain new features; new inventory work
belongs in #3.

## Recommended path (not executed in this sprint — scope/risk)

1. Confirm with product/data whether any real tenant data lives exclusively
   in `inventory_items` (#1/#2) that hasn't been migrated to
   `universal_item_master` (#3).
2. If not, deprecate #1 and #2: stop routing new frontend work to them,
   add a sunset date, then remove the routers/CRUD/model once confirmed
   unused.
3. If real data exists only in `inventory_items`, write a one-time backfill
   migration into `universal_item_master` before deprecating #1/#2 — do
   **not** attempt to keep both in sync going forward; that's the current
   bug, not a design to preserve.

This wasn't done here because it's a data-migration decision requiring
product input, not a code-correctness bug — attempting it inside a
scoped, unattended bug-fix sprint risked silent data loss.
