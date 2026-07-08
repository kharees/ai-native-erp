import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud import universal_ledger as crud
from app.schemas import universal_ledger as schemas
from app.schemas.universal_inventory import PaginatedResponse
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.get("/", response_model=PaginatedResponse[schemas.UniversalInventoryLedgerResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Ledger", "Read"))])
async def get_ledger(
    tenant_id: TenantIDDep, 
    db: DBDep, 
    limit: int = 20, 
    offset: int = 0,
    item_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    bin_id: uuid.UUID | None = None,
    reference_type: str | None = None
):
    items, total = await crud.list_ledger_entries(db, tenant_id, limit, offset, item_id, warehouse_id, bin_id, reference_type)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
