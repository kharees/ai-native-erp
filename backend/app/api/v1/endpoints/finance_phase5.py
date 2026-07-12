from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.middleware.tenant_auth import get_verified_tenant_id
from app.middleware.rbac import RequirePermission
from app.services.audit import AuditLogger

from app.services.finance_ai_copilot import finance_ai_service
from app.schemas.finance_phase5 import (
    AIChatRequest, AIChatResponse,
    AIFinanceInsightOut
)

log = structlog.get_logger(__name__)
router = APIRouter()

def get_user_id(request: Request) -> UUID:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user context")
    return user_id

@router.post("/chat", response_model=AIChatResponse, dependencies=[Depends(RequirePermission("Finance", "AICopilot", "Read"))])
async def cfo_copilot_chat(request: Request, payload: AIChatRequest, db: AsyncSession = Depends(get_db)):
    """Natural Language Interface for the CFO Copilot"""
    tenant_id = await get_verified_tenant_id(request)
    user_id = get_user_id(request)
    
    result = await finance_ai_service.process_chat_query(db, tenant_id, user_id, payload.prompt)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE_AI", action_type="COPILOT_CHAT")
    return result

@router.post("/scan-fraud", response_model=List[AIFinanceInsightOut], dependencies=[Depends(RequirePermission("Finance", "AICopilot", "Create"))])
async def trigger_fraud_scan(request: Request, db: AsyncSession = Depends(get_db)):
    """Manually triggers the AI risk engine to scan the GL for anomalies"""
    tenant_id = await get_verified_tenant_id(request)
    result = await finance_ai_service.scan_for_fraud_and_risks(db, tenant_id)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE_AI", action_type="FRAUD_SCAN")
    return result

@router.get("/insights", response_model=List[AIFinanceInsightOut], dependencies=[Depends(RequirePermission("Finance", "AICopilot", "Read"))])
async def list_ai_insights(request: Request, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Returns the latest AI insights, fraud alerts, and recommendations"""
    tenant_id = await get_verified_tenant_id(request)
    return await finance_ai_service.get_insights(db, tenant_id=tenant_id, skip=skip, limit=limit)
