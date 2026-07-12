from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.middleware.tenant_auth import get_verified_tenant_id
from app.middleware.rbac import RequirePermission
from app.schemas.migration_ai_copilot import (
    DataQualityReportOut, ErrorAnalysisRequest, ErrorAnalysisOut,
    CleansingSuggestionsOut, ChatRequest, ChatResponseOut
)
from app.services.migration_ai_copilot import MigrationAICopilotService
from app.services.audit import AuditLogger

router = APIRouter()

@router.get("/{session_id}/data-quality", response_model=DataQualityReportOut, dependencies=[Depends(RequirePermission("Migration", "System", "Read"))])
async def get_data_quality(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        return await MigrationAICopilotService.analyze_data_quality(db, tenant_id, session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/analyze-error", response_model=ErrorAnalysisOut, dependencies=[Depends(RequirePermission("Migration", "System", "Read"))])
async def analyze_error(
    request: Request,
    session_id: uuid.UUID,
    payload: ErrorAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    # Does not require DB interaction for current heuristic engine
    return MigrationAICopilotService.analyze_error_root_cause(payload.error_message, payload.row_data)

@router.get("/{session_id}/cleansing-suggestions", response_model=CleansingSuggestionsOut, dependencies=[Depends(RequirePermission("Migration", "System", "Read"))])
async def get_cleansing_suggestions(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        return await MigrationAICopilotService.suggest_cleansing_rules(db, tenant_id, session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/chat", response_model=ChatResponseOut, dependencies=[Depends(RequirePermission("Migration", "System", "Read"))])
async def ai_chat(
    request: Request,
    session_id: uuid.UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION_AI", action_type="CHAT_QUERY", resource_id=str(session_id))
    return await MigrationAICopilotService.natural_language_query(db, tenant_id, session_id, payload.query)
