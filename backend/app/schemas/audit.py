"""
app/schemas/audit.py
====================
Pydantic schemas for the Audit & Activity Logging module.
"""

from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class TenantAuditLogBase(BaseModel):
    action_category: str = Field(..., max_length=64)
    action_type: str = Field(..., max_length=64)
    action_source: str = Field(default="API", max_length=32)
    resource_id: Optional[str] = Field(None, max_length=128)
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = Field(None, max_length=64)
    user_agent: Optional[str] = Field(None, max_length=512)
    correlation_id: Optional[str] = Field(None, max_length=128)

class TenantAuditLogResponse(TenantAuditLogBase):
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
