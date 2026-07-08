"""
app/api/v1/endpoints/audit.py
=============================
Router for the Enterprise Audit & Activity Logging Dashboard.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.audit import TenantAuditLog
from app.schemas.audit import TenantAuditLogResponse
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()

@router.get("/", response_model=List[TenantAuditLogResponse])
async def list_audit_logs(
    tenant_id: TenantIDDep,
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user"),
    action_category: Optional[str] = Query(None, description="Filter by category (e.g. AUTH, RBAC)"),
    action_type: Optional[str] = Query(None, description="Filter by exact action type"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation chain"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="Audit", feature="Logs", action="Read"))
):
    """
    Retrieve audit logs with powerful filtering capabilities.
    Only users with Audit -> Logs -> Read permissions can access this.
    """
    stmt = select(TenantAuditLog).where(TenantAuditLog.tenant_id == tenant_id)
    
    if user_id:
        stmt = stmt.where(TenantAuditLog.user_id == user_id)
    if action_category:
        stmt = stmt.where(TenantAuditLog.action_category == action_category)
    if action_type:
        stmt = stmt.where(TenantAuditLog.action_type == action_type)
    if correlation_id:
        stmt = stmt.where(TenantAuditLog.correlation_id == correlation_id)
        
    stmt = stmt.order_by(desc(TenantAuditLog.created_at)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{log_id}", response_model=TenantAuditLogResponse)
async def get_audit_log(
    log_id: uuid.UUID,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="Audit", feature="Logs", action="Read"))
):
    """
    Retrieve a specific audit log by ID to inspect Old Value -> New Value payloads.
    """
    stmt = select(TenantAuditLog).where(
        TenantAuditLog.id == log_id,
        TenantAuditLog.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    log_record = result.scalar_one_or_none()
    
    if not log_record:
        raise HTTPException(status_code=404, detail="Audit log not found")
        
    return log_record

# NOTE: Immutability Enforced
# There are intentionally NO POST, PATCH, or DELETE endpoints in this router.
# Audit logs are strictly written by backend services.
