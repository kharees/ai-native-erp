"""
app/api/v1/endpoints/organization.py
====================================
Router for Organization Management including Branches, Departments, and Warehouses.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.organization import TenantBranch, TenantDepartment, TenantWarehouse
from app.models.tenants import Tenant
from app.schemas.organization import (
    TenantBranchCreate, TenantBranchUpdate, TenantBranchResponse,
    TenantDepartmentCreate, TenantDepartmentUpdate, TenantDepartmentResponse,
    TenantWarehouseCreate, TenantWarehouseUpdate, TenantWarehouseResponse,
    TenantSettingsUpdate, TenantResponse
)
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()

# ---------------------------------------------------------------------------
# Tenant Organization Settings
# ---------------------------------------------------------------------------
@router.get("/", response_model=TenantResponse, dependencies=[Depends(RequirePermission("Organization", "Profile", "Read"))])
async def get_organization_profile(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Get organization profile and global settings."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    return tenant

@router.patch("/", response_model=TenantResponse, dependencies=[Depends(RequirePermission("Organization", "Profile", "Update"))])
async def update_organization_settings(
    update_data: TenantSettingsUpdate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Update organization business settings or company info."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(tenant, key, value)
        
    await db.commit()
    await db.refresh(tenant)
    return tenant

# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------
@router.post("/branches", response_model=TenantBranchResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Organization", "Branches", "Create"))])
async def create_branch(
    branch: TenantBranchCreate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    db_branch = TenantBranch(**branch.model_dump(), tenant_id=tenant_id)
    db.add(db_branch)
    await db.commit()
    await db.refresh(db_branch)
    return db_branch

@router.get("/branches", response_model=List[TenantBranchResponse], dependencies=[Depends(RequirePermission("Organization", "Branches", "Read"))])
async def list_branches(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TenantBranch).where(TenantBranch.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.patch("/branches/{branch_id}", response_model=TenantBranchResponse, dependencies=[Depends(RequirePermission("Organization", "Branches", "Update"))])
async def update_branch(
    branch_id: uuid.UUID,
    branch_update: TenantBranchUpdate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TenantBranch).where(
        TenantBranch.id == branch_id,
        TenantBranch.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    db_branch = result.scalar_one_or_none()
    
    if not db_branch:
        raise HTTPException(status_code=404, detail="Branch not found")
        
    update_dict = branch_update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_branch, key, value)
        
    await db.commit()
    await db.refresh(db_branch)
    return db_branch

# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------
@router.post("/departments", response_model=TenantDepartmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Organization", "Departments", "Create"))])
async def create_department(
    dept: TenantDepartmentCreate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    db_dept = TenantDepartment(**dept.model_dump(), tenant_id=tenant_id)
    db.add(db_dept)
    await db.commit()
    await db.refresh(db_dept)
    return db_dept

@router.get("/departments", response_model=List[TenantDepartmentResponse], dependencies=[Depends(RequirePermission("Organization", "Departments", "Read"))])
async def list_departments(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TenantDepartment).where(TenantDepartment.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.patch("/departments/{dept_id}", response_model=TenantDepartmentResponse, dependencies=[Depends(RequirePermission("Organization", "Departments", "Update"))])
async def update_department(
    dept_id: uuid.UUID,
    dept_update: TenantDepartmentUpdate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TenantDepartment).where(
        TenantDepartment.id == dept_id,
        TenantDepartment.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    db_dept = result.scalar_one_or_none()
    
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
        
    update_dict = dept_update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_dept, key, value)
        
    await db.commit()
    await db.refresh(db_dept)
    return db_dept

# ---------------------------------------------------------------------------
# Warehouses
# ---------------------------------------------------------------------------
@router.post("/warehouses", response_model=TenantWarehouseResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Organization", "Warehouses", "Create"))])
async def create_warehouse(
    warehouse: TenantWarehouseCreate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    db_wh = TenantWarehouse(**warehouse.model_dump(), tenant_id=tenant_id)
    db.add(db_wh)
    await db.commit()
    await db.refresh(db_wh)
    return db_wh

@router.get("/warehouses", response_model=List[TenantWarehouseResponse], dependencies=[Depends(RequirePermission("Organization", "Warehouses", "Read"))])
async def list_warehouses(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TenantWarehouse).where(TenantWarehouse.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.patch("/warehouses/{warehouse_id}", response_model=TenantWarehouseResponse, dependencies=[Depends(RequirePermission("Organization", "Warehouses", "Update"))])
async def update_warehouse(
    warehouse_id: uuid.UUID,
    wh_update: TenantWarehouseUpdate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TenantWarehouse).where(
        TenantWarehouse.id == warehouse_id,
        TenantWarehouse.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    db_wh = result.scalar_one_or_none()
    
    if not db_wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
        
    update_dict = wh_update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_wh, key, value)
        
    await db.commit()
    await db.refresh(db_wh)
    return db_wh
