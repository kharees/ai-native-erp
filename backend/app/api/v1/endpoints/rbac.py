"""
app/api/v1/endpoints/rbac.py
============================
Router for Role-Based Access Control configuration.
"""

import uuid
from typing import List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, delete

from app.core.database import get_db
from app.models.rbac import TenantRole, TenantPermission, TenantRolePermission, TenantUserRole
from app.schemas.rbac import (
    TenantRoleCreate, TenantRoleUpdate, TenantRoleResponse,
    TenantPermissionResponse, TenantRolePermissionCreate, TenantRolePermissionResponse,
    TenantUserRoleCreate, TenantUserRoleResponse
)
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
@router.post("/roles", response_model=TenantRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: Request,
    role_in: TenantRoleCreate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Roles", action="Create"))
):
    """Create a new custom role."""
    current_user_id = getattr(request.state, "user_id", None)
    
    db_role = TenantRole(
        **role_in.model_dump(), 
        tenant_id=tenant_id, 
        is_system=False,
        created_by=uuid.UUID(current_user_id) if current_user_id else None
    )
    db.add(db_role)
    await db.commit()
    await db.refresh(db_role)
    return db_role

@router.get("/roles", response_model=List[TenantRoleResponse])
async def list_roles(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Roles", action="Read"))
):
    """List all available roles (system roles + tenant custom roles)."""
    stmt = select(TenantRole).where(
        or_(
            TenantRole.tenant_id == tenant_id,
            TenantRole.tenant_id.is_(None)
        ),
        TenantRole.deleted_at.is_(None)
    ).order_by(TenantRole.hierarchy_level)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/roles/{role_id}", response_model=TenantRoleResponse)
async def update_role(
    request: Request,
    role_id: uuid.UUID,
    role_in: TenantRoleUpdate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Roles", action="Update"))
):
    """Update a custom role."""
    current_user_id = getattr(request.state, "user_id", None)
    
    stmt = select(TenantRole).where(
        TenantRole.id == role_id,
        TenantRole.tenant_id == tenant_id,
        TenantRole.is_system.is_(False),
        TenantRole.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    db_role = result.scalar_one_or_none()
    
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found or is a system role")
        
    update_data = role_in.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_role, k, v)
        
    db_role.updated_at = datetime.now(timezone.utc)
    if current_user_id:
        db_role.updated_by = uuid.UUID(current_user_id)
        
    await db.commit()
    await db.refresh(db_role)
    return db_role

@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    request: Request,
    role_id: uuid.UUID,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Roles", action="Delete"))
):
    """Soft delete a custom role."""
    current_user_id = getattr(request.state, "user_id", None)
    
    stmt = select(TenantRole).where(
        TenantRole.id == role_id,
        TenantRole.tenant_id == tenant_id,
        TenantRole.is_system.is_(False),
        TenantRole.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    db_role = result.scalar_one_or_none()
    
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found or is a system role")
        
    db_role.deleted_at = datetime.now(timezone.utc)
    if current_user_id:
        db_role.updated_by = uuid.UUID(current_user_id)
        
    await db.commit()
    return None

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
@router.get("/permissions", response_model=List[TenantPermissionResponse])
async def list_permissions(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Permissions", action="Read"))
):
    """List all available atomic permissions."""
    stmt = select(TenantPermission).where(TenantPermission.deleted_at.is_(None)).order_by(TenantPermission.module, TenantPermission.feature)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/permissions", status_code=status.HTTP_200_OK)
async def update_role_permissions_matrix(
    request: Request,
    tenant_id: TenantIDDep,
    matrix: List[dict] = Body(...),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Permissions", action="Update"))
):
    """
    Batch update permissions for multiple roles (Permission Matrix).
    matrix should be a list of dicts: [{"role_id": "...", "permission_ids": ["...", "..."]}]
    """
    current_user_id = getattr(request.state, "user_id", None)
    created_by_uuid = uuid.UUID(current_user_id) if current_user_id else None

    # First, validate that all role_ids belong to the tenant or are modifiable
    role_ids = [uuid.UUID(item["role_id"]) for item in matrix]
    role_stmt = select(TenantRole.id).where(
        TenantRole.id.in_(role_ids),
        or_(
            TenantRole.tenant_id == tenant_id,
            TenantRole.tenant_id.is_(None) # For some cases where system roles might allow permission updates, though usually they shouldn't. Let's allow it for simplicity if the user has permission.
        )
    )
    valid_roles_res = await db.execute(role_stmt)
    valid_roles = [r for r in valid_roles_res.scalars().all()]
    
    for item in matrix:
        r_id = uuid.UUID(item["role_id"])
        if r_id not in valid_roles:
            continue # Skip invalid roles
            
        # Delete existing permissions for this role
        del_stmt = delete(TenantRolePermission).where(TenantRolePermission.role_id == r_id)
        await db.execute(del_stmt)
        
        # Add new permissions
        for p_id in item.get("permission_ids", []):
            db_rp = TenantRolePermission(
                role_id=r_id,
                permission_id=uuid.UUID(p_id),
                created_by=created_by_uuid
            )
            db.add(db_rp)
            
    await db.commit()
    return {"message": "Permissions updated successfully"}

# ---------------------------------------------------------------------------
# Role Permissions Assignment (Per Role)
# ---------------------------------------------------------------------------
@router.post("/roles/{role_id}/permissions", response_model=TenantRolePermissionResponse, status_code=status.HTTP_201_CREATED)
async def assign_permission_to_role(
    request: Request,
    role_id: uuid.UUID,
    perm_in: TenantRolePermissionCreate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Permissions", action="Create"))
):
    """Assign a permission to a specific role."""
    current_user_id = getattr(request.state, "user_id", None)
    
    # Ensure role belongs to tenant
    role_stmt = select(TenantRole).where(TenantRole.id == role_id, or_(TenantRole.tenant_id == tenant_id, TenantRole.tenant_id.is_(None)))
    role_res = await db.execute(role_stmt)
    if not role_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Role not found")
        
    db_rp = TenantRolePermission(
        **perm_in.model_dump(), 
        role_id=role_id,
        created_by=uuid.UUID(current_user_id) if current_user_id else None
    )
    db.add(db_rp)
    await db.commit()
    await db.refresh(db_rp)
    return db_rp

@router.get("/roles/{role_id}/permissions", response_model=List[TenantRolePermissionResponse])
async def get_role_permissions(
    role_id: uuid.UUID,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Permissions", action="Read"))
):
    """Get all permissions assigned to a role."""
    stmt = select(TenantRolePermission).where(TenantRolePermission.role_id == role_id)
    result = await db.execute(stmt)
    return result.scalars().all()

# ---------------------------------------------------------------------------
# User Role Assignment
# ---------------------------------------------------------------------------
@router.post("/users/roles", response_model=TenantUserRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    request: Request,
    assignment_in: TenantUserRoleCreate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Roles", action="Create"))
):
    """Assign a role to a user, optionally scoped to a branch or warehouse."""
    current_user_id = getattr(request.state, "user_id", None)
    
    db_ur = TenantUserRole(
        **assignment_in.model_dump(), 
        tenant_id=tenant_id,
        created_by=uuid.UUID(current_user_id) if current_user_id else None
    )
    db.add(db_ur)
    await db.commit()
    await db.refresh(db_ur)
    return db_ur

@router.get("/users/{user_id}/roles", response_model=List[TenantUserRoleResponse])
async def get_user_roles(
    user_id: uuid.UUID,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Roles", action="Read"))
):
    """Get all roles assigned to a user."""
    stmt = select(TenantUserRole).where(
        TenantUserRole.user_id == user_id,
        TenantUserRole.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    return result.scalars().all()
