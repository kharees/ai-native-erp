from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field, EmailStr

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta

# Customer Group
class UniversalCustomerGroupBase(BaseModel):
    name: str = Field(..., max_length=128)
    description: str | None = None

class UniversalCustomerGroupCreate(UniversalCustomerGroupBase):
    pass

class UniversalCustomerGroupUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    description: str | None = None

class UniversalCustomerGroupResponse(UniversalCustomerGroupBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Customer Type
class UniversalCustomerTypeBase(BaseModel):
    name: str = Field(..., max_length=128)

class UniversalCustomerTypeCreate(UniversalCustomerTypeBase):
    pass

class UniversalCustomerTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)

class UniversalCustomerTypeResponse(UniversalCustomerTypeBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Customer Category
class UniversalCustomerCategoryBase(BaseModel):
    name: str = Field(..., max_length=128)

class UniversalCustomerCategoryCreate(UniversalCustomerCategoryBase):
    pass

class UniversalCustomerCategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)

class UniversalCustomerCategoryResponse(UniversalCustomerCategoryBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Customer
class UniversalCustomerBase(BaseModel):
    group_id: uuid.UUID | None = None
    type_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    name: str = Field(..., max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)
    gst_number: str | None = Field(None, max_length=15)
    pan: str | None = Field(None, max_length=10)
    credit_limit: float = Field(0.0, ge=0)
    credit_days: int = Field(0, ge=0)
    currency: str = Field("INR", max_length=3)
    status: str = Field("ACTIVE", max_length=32)

class UniversalCustomerCreate(UniversalCustomerBase):
    pass

class UniversalCustomerUpdate(BaseModel):
    group_id: uuid.UUID | None = None
    type_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)
    gst_number: str | None = Field(None, max_length=15)
    pan: str | None = Field(None, max_length=10)
    credit_limit: float | None = Field(None, ge=0)
    credit_days: int | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=3)
    status: str | None = Field(None, max_length=32)

class UniversalCustomerResponse(UniversalCustomerBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Customer Contact
class UniversalCustomerContactBase(BaseModel):
    customer_id: uuid.UUID
    name: str = Field(..., max_length=255)
    role: str | None = Field(None, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)

class UniversalCustomerContactCreate(UniversalCustomerContactBase):
    pass

class UniversalCustomerContactUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    role: str | None = Field(None, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)

class UniversalCustomerContactResponse(UniversalCustomerContactBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Customer Address
class UniversalCustomerAddressBase(BaseModel):
    customer_id: uuid.UUID
    address_type: str = Field(..., max_length=32)
    line1: str
    city: str | None = Field(None, max_length=128)
    state: str | None = Field(None, max_length=128)
    postal_code: str | None = Field(None, max_length=32)
    country: str | None = Field(None, max_length=128)

class UniversalCustomerAddressCreate(UniversalCustomerAddressBase):
    pass

class UniversalCustomerAddressUpdate(BaseModel):
    address_type: str | None = Field(None, max_length=32)
    line1: str | None = None
    city: str | None = Field(None, max_length=128)
    state: str | None = Field(None, max_length=128)
    postal_code: str | None = Field(None, max_length=32)
    country: str | None = Field(None, max_length=128)

class UniversalCustomerAddressResponse(UniversalCustomerAddressBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
