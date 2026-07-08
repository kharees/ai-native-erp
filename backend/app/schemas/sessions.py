"""
app/schemas/sessions.py
=======================
Pydantic schemas for the Session & Device Management module.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class TenantSessionBase(BaseModel):
    device_fingerprint: Optional[str] = Field(None, max_length=255)
    ip_address: Optional[str] = Field(None, max_length=64)
    browser: Optional[str] = Field(None, max_length=64)
    os: Optional[str] = Field(None, max_length=64)

class TenantSessionResponse(TenantSessionBase):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    is_active: bool
    last_active_at: datetime
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TenantDeviceBase(BaseModel):
    device_fingerprint: str = Field(..., max_length=255)
    browser: Optional[str] = Field(None, max_length=64)
    os: Optional[str] = Field(None, max_length=64)

class TenantDeviceResponse(TenantDeviceBase):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    last_ip_address: Optional[str] = None
    is_trusted: bool
    last_seen_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
