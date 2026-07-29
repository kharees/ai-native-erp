"""
app/agent/tools/inventory_tools.py
=====================================
Second tool registry for the AI OS layer (audit #3): 3 LLM-callable tools
over the existing Inventory module (app/crud/universal_warehousing.py,
universal_inventory.py). Follows the exact same contract as
app/agent/tools/billing_tools.py -- see that file's docstring for the full
rationale (tenant_id/user_id/idempotency_key never in input_schema,
unit-of-work via db_session(), @agent_tool reuse). Only what's specific to
Inventory is documented here.

execute_stock_movement's error classification diverges from its HTTP
endpoint (app/api/v1/endpoints/universal_warehousing.py's
/stock/transactions, which maps both ValueError and IntegrityError to a 409
conflict): here they become HTTPException(400) instead. In the orchestrator,
a 409 is classified as STUCK_CONFLICT -- "don't retry, tell the user to
check state manually" -- which is correct for a stuck idempotency claim but
wrong for an ordinary "insufficient stock, try a smaller quantity"
rejection. 409/STUCK_CONFLICT stays reserved exclusively for the
idempotency-claim conflict below, matching create_invoice/record_payment's
existing precedent (their only 409 is claim.conflict, never a business-rule
rejection).

get_stock_balance's crud function is new (app/crud/universal_warehousing.py
:get_stock_balance) -- no existing function answered "total stock for this
item at this warehouse" without already knowing a specific bin_id.

Consolidation addition (get_dead_stock_report/get_expiring_batches_report/
get_demand_forecast): these wrap app/services/universal_intelligence.py's
real query helpers directly (_get_dead_stock_candidates/_get_expiring_
batches/_get_forecast_candidates -- genuine SQL, no fabricated data, see
that module's own docstring). That file's process_copilot_query (a
keyword router that made its own separate get_ai_provider() call per
intent) and get_dashboard's own AI-narration step are deliberately NOT
wrapped here -- every other tool in this whole registry is a pure data
fetch, with narration coming from the ONE consolidated orchestrator model
call, not a second, per-tool LLM call nested inside a "tool". get_dashboard
remains available as its own direct REST endpoint (GET /universal-
intelligence/dashboard) for a full pre-composed view; it's just not
wired into the tool-calling surface.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.agent.tools.base import ToolDefinition
from app.core.database import db_session
from app.crud import universal_inventory as crud_items
from app.crud import universal_warehousing as crud_warehousing
from app.schemas.universal_inventory import UniversalItemMasterResponse
from app.schemas.universal_warehousing import StockMovementRequest, StockTransactionResponse
from app.services.idempotency import claim_idempotency_key, complete_idempotency_key
from app.services.agent_adapters.base import agent_tool
from app.services.universal_intelligence import (
    _get_dead_stock_candidates,
    _get_expiring_batches,
    _get_forecast_candidates,
)


# ---------------------------------------------------------------------------
# get_stock_balance
# ---------------------------------------------------------------------------

_GET_STOCK_BALANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_id": {"type": "string", "format": "uuid"},
        "warehouse_id": {"type": "string", "format": "uuid"},
        "bin_id": {
            "type": "string", "format": "uuid",
            "description": "Omit for the total across all bins in the warehouse.",
        },
    },
    "required": ["item_id", "warehouse_id"],
}


@agent_tool
async def handle_get_stock_balance(
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    bin_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    async with db_session() as db:
        balance = await crud_warehousing.get_stock_balance(db, tenant_id, item_id, warehouse_id, bin_id)
        return {
            "item_id": str(balance["item_id"]),
            "warehouse_id": str(balance["warehouse_id"]),
            "bin_id": str(balance["bin_id"]) if balance["bin_id"] else None,
            "quantity_on_hand": float(balance["quantity_on_hand"]),
            "quantity_reserved": float(balance["quantity_reserved"]),
            "quantity_allocated": float(balance["quantity_allocated"]),
        }


# ---------------------------------------------------------------------------
# execute_stock_movement
# ---------------------------------------------------------------------------

_EXECUTE_STOCK_MOVEMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_id": {"type": "string", "format": "uuid"},
        "warehouse_id": {"type": "string", "format": "uuid"},
        "bin_id": {"type": "string", "format": "uuid"},
        "batch_id": {"type": "string", "format": "uuid"},
        "serial_numbers": {"type": "array", "items": {"type": "string"}},
        "destination_warehouse_id": {
            "type": "string", "format": "uuid",
            "description": "Required when transaction_type is TRANSFER.",
        },
        "destination_bin_id": {"type": "string", "format": "uuid"},
        "transaction_type": {"type": "string", "enum": ["IN", "OUT", "ADJUST", "TRANSFER"]},
        "reference_type": {"type": "string", "maxLength": 64},
        "reference_id": {"type": "string", "maxLength": 128},
        "quantity": {"type": "number", "exclusiveMinimum": 0},
        "metadata": {
            "type": "object",
            "description": "Arbitrary key/value data about this movement, e.g. unit_cost.",
        },
    },
    "required": ["item_id", "warehouse_id", "transaction_type", "reference_type", "quantity"],
}


@agent_tool
async def handle_execute_stock_movement(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: str,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    transaction_type: str,
    reference_type: str,
    quantity: float,
    bin_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    serial_numbers: list[str] | None = None,
    destination_warehouse_id: uuid.UUID | None = None,
    destination_bin_id: uuid.UUID | None = None,
    reference_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async with db_session() as db:
        claim = await claim_idempotency_key(db, tenant_id, "agent.execute_stock_movement", idempotency_key)
        if claim.replay_response is not None:
            return claim.replay_response
        if claim.conflict:
            raise HTTPException(
                status_code=409,
                detail="An execute_stock_movement call with this idempotency key is already in progress.",
            )

        payload = StockMovementRequest(
            item_id=item_id,
            warehouse_id=warehouse_id,
            bin_id=bin_id,
            batch_id=batch_id,
            serial_numbers=serial_numbers,
            destination_warehouse_id=destination_warehouse_id,
            destination_bin_id=destination_bin_id,
            transaction_type=transaction_type,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity=quantity,
            metadata=metadata or {},
        )
        try:
            txn = await crud_warehousing.execute_stock_movement(db, tenant_id, user_id, payload)
        except (ValueError, IntegrityError) as exc:
            # See module docstring: deliberately 400 (-> VALIDATION_ERROR),
            # not the HTTP endpoint's 409 -- STUCK_CONFLICT stays reserved
            # for the idempotency claim conflict above.
            detail = str(exc) if isinstance(exc, ValueError) else "Stock movement failed a database constraint."
            raise HTTPException(status_code=400, detail=detail)

        response_body = StockTransactionResponse.model_validate(txn).model_dump(mode="json", by_alias=True)

        if claim.should_complete:
            await complete_idempotency_key(
                db, tenant_id, "agent.execute_stock_movement", idempotency_key, txn.id, response_body
            )

        return response_body


# ---------------------------------------------------------------------------
# search_item
# ---------------------------------------------------------------------------

_SEARCH_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "search": {"type": "string", "description": "Partial or full item name, SKU, or item code to search for"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
    },
    "required": ["search"],
}


@agent_tool
async def handle_search_item(
    tenant_id: uuid.UUID,
    search: str,
    limit: int = 20,
) -> dict[str, Any]:
    # Read-only: no user_id, no idempotency concern.
    async with db_session() as db:
        # Exact-code resolution first (sku/item_code/barcode, then OEM/
        # aftermarket/competitor/barcode aliases via
        # find_item_by_any_code) -- the same resolver order_capture.py's
        # photo-capture pipeline uses, so a manual search for an
        # aftermarket part number resolves to the same item it would from
        # a photo. Only falls through to the substring name/sku/item_code
        # search below when no exact code match exists.
        exact_match = await crud_items.find_item_by_any_code(db, tenant_id, search)
        if exact_match is not None:
            return {
                "items": [UniversalItemMasterResponse.model_validate(exact_match).model_dump(mode="json")],
                "total": 1,
            }

        items, total = await crud_items.list_items(db, tenant_id, limit=limit, offset=0, search=search)
        return {
            "items": [UniversalItemMasterResponse.model_validate(obj).model_dump(mode="json") for obj in items],
            "total": total,
        }


# ---------------------------------------------------------------------------
# get_dead_stock_report / get_expiring_batches_report / get_demand_forecast
# ---------------------------------------------------------------------------

_NO_PARAMS_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": []}


@agent_tool
async def handle_get_dead_stock_report(tenant_id: uuid.UUID) -> dict[str, Any]:
    async with db_session() as db:
        candidates = await _get_dead_stock_candidates(db, tenant_id)
        return {
            "items": [
                {**c, "item_id": str(c["item_id"])} for c in candidates
            ],
            "total": len(candidates),
        }


@agent_tool
async def handle_get_expiring_batches_report(tenant_id: uuid.UUID) -> dict[str, Any]:
    async with db_session() as db:
        batches = await _get_expiring_batches(db, tenant_id)
        return {
            "batches": [
                {**b, "batch_id": str(b["batch_id"]), "item_id": str(b["item_id"]), "expiry_date": b["expiry_date"].isoformat()}
                for b in batches
            ],
            "total": len(batches),
        }


@agent_tool
async def handle_get_demand_forecast(tenant_id: uuid.UUID) -> dict[str, Any]:
    async with db_session() as db:
        forecasts = await _get_forecast_candidates(db, tenant_id)
        return {
            "items": [
                {**f, "item_id": str(f["item_id"])} for f in forecasts
            ],
            "total": len(forecasts),
        }


INVENTORY_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_stock_balance",
        description=(
            "Look up current stock for an item at a warehouse. Omit bin_id "
            "for the total across all bins in that warehouse."
        ),
        input_schema=_GET_STOCK_BALANCE_SCHEMA,
        required_permission=("UniversalInventory", "Stock", "Read"),
        handler=handle_get_stock_balance,
    ),
    ToolDefinition(
        name="execute_stock_movement",
        description=(
            "Move stock: IN (receive), OUT (issue/consume), ADJUST (correct "
            "on-hand quantity), or TRANSFER (move between warehouses/bins, "
            "requires destination_warehouse_id). Fails if it would leave "
            "negative stock at the source location."
        ),
        input_schema=_EXECUTE_STOCK_MOVEMENT_SCHEMA,
        required_permission=("UniversalInventory", "Stock", "Create"),
        handler=handle_execute_stock_movement,
        requires_confirmation=True,
    ),
    ToolDefinition(
        name="search_item",
        description=(
            "Search for existing items by name, SKU, or item code (partial "
            "match). Use this to find an item_id before checking stock or "
            "recording a movement."
        ),
        input_schema=_SEARCH_ITEM_SCHEMA,
        required_permission=("UniversalInventory", "Items", "Read"),
        handler=handle_search_item,
    ),
    ToolDefinition(
        name="get_dead_stock_report",
        description=(
            "Items with real on-hand stock that haven't moved in a long "
            "time (dead/slow-moving stock), with real tied-up value from "
            "ledger cost history."
        ),
        input_schema=_NO_PARAMS_SCHEMA,
        required_permission=("UniversalInventory", "Intelligence", "Read"),
        handler=handle_get_dead_stock_report,
    ),
    ToolDefinition(
        name="get_expiring_batches_report",
        description="Real batches with remaining stock expiring soon, soonest first.",
        input_schema=_NO_PARAMS_SCHEMA,
        required_permission=("UniversalInventory", "Intelligence", "Read"),
        handler=handle_get_expiring_batches_report,
    ),
    ToolDefinition(
        name="get_demand_forecast",
        description=(
            "Top-moving items by trailing 90-day outbound volume, with a "
            "real linear 30-day demand projection from ledger history."
        ),
        input_schema=_NO_PARAMS_SCHEMA,
        required_permission=("UniversalInventory", "Intelligence", "Read"),
        handler=handle_get_demand_forecast,
    ),
]
