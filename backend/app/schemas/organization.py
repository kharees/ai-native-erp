"""
app/schemas/organization.py
===========================
Pydantic schemas for Organization Management (Tenant, Branches, Departments, Warehouses).
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# Base schemas
class TenantBranchBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=64)
    address: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

class TenantDepartmentBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=64)
    parent_id: Optional[UUID] = None
    is_active: bool = True

class TenantWarehouseBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=64)
    branch_id: Optional[UUID] = None
    address: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

# Create schemas
class TenantBranchCreate(TenantBranchBase):
    pass

class TenantDepartmentCreate(TenantDepartmentBase):
    pass

class TenantWarehouseCreate(TenantWarehouseBase):
    pass

# Update schemas
class TenantBranchUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=64)
    address: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class TenantDepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=64)
    parent_id: Optional[UUID] = None
    is_active: Optional[bool] = None

class TenantWarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=64)
    branch_id: Optional[UUID] = None
    address: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class TenantSettingsUpdate(BaseModel):
    company_info: Optional[Dict[str, Any]] = None
    business_settings: Optional[Dict[str, Any]] = None

# Response schemas
class TenantBranchResponse(TenantBranchBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TenantDepartmentResponse(TenantDepartmentBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TenantWarehouseResponse(TenantWarehouseBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    company_info: Dict[str, Any]
    business_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
