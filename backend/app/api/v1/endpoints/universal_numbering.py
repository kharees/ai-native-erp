import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_numbering as crud
from app.schemas import universal_numbering as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

def _not_found(entity: str, id: uuid.UUID) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} '{id}' not found.")

@router.post("/", response_model=schemas.UniversalNumberSeriesResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Settings", "Create"))])
async def create_series(payload: schemas.UniversalNumberSeriesCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_series(db, tenant_id, payload)

@router.get("/{id}", response_model=schemas.UniversalNumberSeriesResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Settings", "Read"))])
async def get_series(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_series(db, tenant_id, id)
    if not obj: raise _not_found("NumberSeries", id)
    return obj

@router.post("/generate/{entity_type}", response_model=dict, dependencies=[Depends(RequirePermission("UniversalBilling", "Settings", "Update"))])
async def generate_next_number(entity_type: str, tenant_id: TenantIDDep, db: DBDep):
    num = await crud.generate_next_number(db, tenant_id, entity_type)
    return {"entity_type": entity_type, "next_number": num}
