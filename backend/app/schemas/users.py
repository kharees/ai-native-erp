"""
app/schemas/users.py
====================
Pydantic schemas for User Management.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class UserProfileBase(BaseModel):
    first_name: Optional[str] = Field(None, max_length=128)
    last_name: Optional[str] = Field(None, max_length=128)
    profile_image: Optional[str] = None
    phone: Optional[str] = None
    timezone: str = "UTC"
    locale: str = "en"
    employee_code: Optional[str] = Field(None, max_length=64)
    status: str = "Active"
    designation: Optional[str] = Field(None, max_length=128)
    department_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    role: str = "member"
    is_active: bool = True

class UserProfileCreate(UserProfileBase):
    user_id: UUID

class UserProfileProvision(UserProfileBase):
    email: EmailStr
    password: str = Field(..., min_length=8)
    roles: List[UUID] = Field(default_factory=list)

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=128)
    last_name: Optional[str] = Field(None, max_length=128)
    profile_image: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    employee_code: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = None
    designation: Optional[str] = Field(None, max_length=128)
    department_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    preferences: Optional[Dict[str, Any]] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserProfileResponse(UserProfileBase):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
