import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_collections as crud
from app.schemas import universal_collections as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.get("/status/{customer_id}", response_model=schemas.CollectionStatusResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Collections", "Read"))])
async def get_collection_status(customer_id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    status_data = await crud.get_collection_status(db, tenant_id, customer_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Customer not found")
    return status_data

@router.get("/aging/{customer_id}", response_model=schemas.AgingBucketResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Collections", "Read"))])
async def get_aging_buckets(customer_id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    return await crud.get_aging_buckets(db, tenant_id, customer_id)
