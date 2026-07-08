"""
app/services/audit.py
=====================
Service layer for immutable enterprise activity logging.
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import TenantAuditLog

class AuditLogger:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        request: Request,
        action_category: str,
        action_type: str,
        resource_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> TenantAuditLog:
        """
        Record a generic system action into the immutable audit ledger.
        Extracts tenant, user, and network context from the FastAPI Request.
        """
        tenant_id = getattr(request.state, "tenant_id", None)
        user_id = getattr(request.state, "user_id", None)
        
        # If tenant_id isn't resolved, we can't record a tenant-bound audit log.
        if not tenant_id:
            return None
            
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        from datetime import datetime, timezone
        audit_log = TenantAuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            action_category=action_category,
            action_type=action_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            action_source="API",
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(audit_log)
        # Note: We do NOT commit here to allow the caller to wrap the audit log
        # in the same transaction as the resource mutation.
        
        return audit_log
