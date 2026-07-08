"""
app/schemas/rbac.py
===================
Pydantic schemas for Role-Based Access Control.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# TenantRole
# ---------------------------------------------------------------------------
class TenantRoleBase(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    hierarchy_level: int = 100

class TenantRoleCreate(TenantRoleBase):
    pass

class TenantRoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    hierarchy_level: Optional[int] = None

class TenantRoleResponse(TenantRoleBase):
    id: UUID
    tenant_id: Optional[UUID] = None
    is_system: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# TenantPermission
# ---------------------------------------------------------------------------
class TenantPermissionBase(BaseModel):
    module: str = Field(..., max_length=64)
    feature: str = Field(..., max_length=64)
    action: str = Field(..., max_length=32)
    description: Optional[str] = None

class TenantPermissionCreate(TenantPermissionBase):
    pass

class TenantPermissionResponse(TenantPermissionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# TenantRolePermission
# ---------------------------------------------------------------------------
class TenantRolePermissionBase(BaseModel):
    permission_id: UUID
    conditions: Dict[str, Any] = Field(default_factory=dict)

class TenantRolePermissionCreate(TenantRolePermissionBase):
    pass

class TenantRolePermissionResponse(TenantRolePermissionBase):
    id: UUID
    role_id: UUID
    created_at: datetime
    created_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# TenantUserRole
# ---------------------------------------------------------------------------
class TenantUserRoleBase(BaseModel):
    role_id: UUID
    branch_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None

class TenantUserRoleCreate(TenantUserRoleBase):
    user_id: UUID

class TenantUserRoleResponse(TenantUserRoleBase):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    created_at: datetime
    created_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)
