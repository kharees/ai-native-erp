from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.core.database import get_db
from app.middleware.tenant_auth import get_verified_tenant_id
from app.middleware.rbac import RequirePermission
from app.models.migration import MigrationSession, MigrationRollbackLog, MigrationReconciliationReport
from app.schemas.migration_execution import (
    ExecutionStatusResponse, RollbackRequest, 
    MigrationRollbackLogOut, ReconciliationReportOut
)
from app.schemas.migration_hub import MigrationSessionOut
from app.services.migration_execution_engine import (
    MigrationExecutionManager, MigrationRollbackEngine, MigrationReconciliationEngine
)
from app.services.audit import AuditLogger

router = APIRouter()

@router.get("/{session_id}/status", response_model=ExecutionStatusResponse)
async def get_execution_status(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    stmt = select(MigrationSession).where(MigrationSession.id == session_id, MigrationSession.tenant_id == tenant_id)
    session = (await db.execute(stmt)).scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return ExecutionStatusResponse(
        session_id=session.id,
        status=session.status,
        progress_percentage=session.progress_percentage,
        imported_records=session.imported_records,
        skipped_records=session.skipped_records,
        failed_records=session.invalid_records, # Simulating failed as invalid for now
        processing_speed_mps=session.processing_speed_mps,
        estimated_remaining_time_sec=session.estimated_remaining_time_sec,
        message="Execution status retrieved successfully"
    )

@router.post("/{session_id}/execute", response_model=MigrationSessionOut, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def execute_migration(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        session = await MigrationExecutionManager.start_execution(db, tenant_id, session_id)
        await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION_EXECUTION", action_type="START", resource_id=str(session_id))
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/pause", response_model=MigrationSessionOut, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def pause_migration(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        session = await MigrationExecutionManager.pause_execution(db, tenant_id, session_id)
        await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION_EXECUTION", action_type="PAUSE", resource_id=str(session_id))
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/resume", response_model=MigrationSessionOut, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def resume_migration(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        session = await MigrationExecutionManager.resume_execution(db, tenant_id, session_id)
        await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION_EXECUTION", action_type="RESUME", resource_id=str(session_id))
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/cancel", response_model=MigrationSessionOut, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def cancel_migration(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        session = await MigrationExecutionManager.cancel_execution(db, tenant_id, session_id)
        await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION_EXECUTION", action_type="CANCEL", resource_id=str(session_id))
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/rollback", response_model=MigrationRollbackLogOut, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def rollback_migration(
    request: Request,
    session_id: uuid.UUID,
    payload: RollbackRequest,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        log = await MigrationRollbackEngine.rollback_session(db, tenant_id, session_id, payload.partial, payload.record_ids)
        await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION_EXECUTION", action_type="ROLLBACK", resource_id=str(session_id))
        return log
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/reconcile", response_model=ReconciliationReportOut, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def generate_reconciliation(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        report = await MigrationReconciliationEngine.generate_report(db, tenant_id, session_id)
        await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION_EXECUTION", action_type="RECONCILE", resource_id=str(session_id))
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
