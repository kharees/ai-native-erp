import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_ai_billing as crud
from app.schemas import universal_ai_billing as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.get("/risk-score/{customer_id}", response_model=schemas.AICreditRiskScoreResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "AI", "Read"))])
async def get_risk_score(customer_id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    result = await crud.calculate_credit_risk(db, tenant_id, customer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result

@router.post("/smart-draft", response_model=schemas.AISmartDraftResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "AI", "Create"))])
async def generate_smart_draft(payload: schemas.AISmartDraftRequest, tenant_id: TenantIDDep, db: DBDep):
    return await crud.generate_smart_draft(db, tenant_id, payload)

@router.get("/fraud-scan", response_model=schemas.PaginatedResponse[schemas.AIFraudAlertResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "AI", "Read"))])
async def scan_fraud(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items = await crud.scan_fraud_anomalies(db, tenant_id)
    return {"items": items, "meta": {"total": len(items), "limit": limit, "offset": offset, "has_more": False}}
