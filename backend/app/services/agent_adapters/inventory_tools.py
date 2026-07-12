"""
app/services/agent_adapters/inventory_tools.py
=================================================
Sprint 5 (#2): agent-safe adapters over app/crud/universal_inventory.py
and app/crud/universal_warehousing.py. See finance_tools.py's module
docstring for the pattern this follows — every function here is
@agent_tool-decorated (no session parameter, enforced at import time),
opens its own db_session() internally, and returns a plain Pydantic
schema rather than a session-bound ORM object.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from app.core.database import db_session
from app.crud import universal_inventory as inv_crud
from app.crud import universal_warehousing as wh_crud
from app.schemas.universal_inventory import (
    UniversalItemMasterCreate,
    UniversalItemMasterResponse,
)
from app.schemas.universal_warehousing import StockMovementRequest, StockTransactionResponse
from app.services.agent_adapters.base import agent_tool


@agent_tool
async def get_item(tenant_id: uuid.UUID, item_id: uuid.UUID) -> Optional[UniversalItemMasterResponse]:
    """Fetch one inventory item master record by id, scoped to tenant_id."""
    async with db_session() as db:
        obj = await inv_crud.get_item(db, tenant_id, item_id)
        return UniversalItemMasterResponse.model_validate(obj) if obj else None


@agent_tool
async def create_item(
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    item_code: str,
    sku: str,
    name: str,
    category_id: Optional[uuid.UUID] = None,
    brand_id: Optional[uuid.UUID] = None,
    uom_id: Optional[uuid.UUID] = None,
) -> UniversalItemMasterResponse:
    """Create a new inventory item master record."""
    async with db_session() as db:
        payload = UniversalItemMasterCreate(
            item_code=item_code,
            sku=sku,
            name=name,
            category_id=category_id,
            brand_id=brand_id,
            uom_id=uom_id,
        )
        obj = await inv_crud.create_item(db, tenant_id, user_id, payload)
        return UniversalItemMasterResponse.model_validate(obj)


@agent_tool
async def execute_stock_movement(
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    transaction_type: str,
    quantity: float,
    reference_type: str,
    reference_id: Optional[str] = None,
    bin_id: Optional[uuid.UUID] = None,
    destination_warehouse_id: Optional[uuid.UUID] = None,
    destination_bin_id: Optional[uuid.UUID] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> StockTransactionResponse:
    """
    Move stock for one item (IN / OUT / ADJUST / TRANSFER). For TRANSFER,
    both the source debit and destination credit legs are written in one
    transaction — see app/crud/universal_warehousing.py::execute_stock_movement.
    """
    async with db_session() as db:
        payload = StockMovementRequest(
            item_id=item_id,
            warehouse_id=warehouse_id,
            bin_id=bin_id,
            destination_warehouse_id=destination_warehouse_id,
            destination_bin_id=destination_bin_id,
            transaction_type=transaction_type,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity=quantity,
            metadata=metadata or {},
        )
        txn = await wh_crud.execute_stock_movement(db, tenant_id, user_id, payload)
        return StockTransactionResponse.model_validate(txn)
