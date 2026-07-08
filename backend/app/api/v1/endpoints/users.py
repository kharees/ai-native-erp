"""
app/api/v1/endpoints/users.py
=============================
Router for enterprise user profile management.
"""

import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from app.core.database import get_db
from app.models.users import UserProfile
from app.models.auth import UserAccount
from app.models.rbac import TenantUserRole
from app.middleware.tenant_auth import TenantIDDep
from app.schemas.users import UserProfileProvision, UserProfileUpdate, UserProfileResponse
from app.core.security import get_password_hash

router = APIRouter()

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user(
    request: Request,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Get the profile of the currently authenticated user."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
        
    stmt = select(UserProfile, UserAccount.email).join(
        UserAccount, UserAccount.id == UserProfile.user_id
    ).where(
        UserProfile.user_id == user_id,
        UserProfile.tenant_id == tenant_id,
        UserProfile.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    user_profile, email = row
    response_data = user_profile.__dict__.copy()
    response_data["email"] = email
    return response_data

@router.post("/", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def provision_user(
    request: Request,
    user_in: UserProfileProvision,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Provision a new user account and profile."""
    current_user_id = getattr(request.state, "user_id", None)
    
    # Check duplicate email
    email_stmt = select(UserAccount).where(UserAccount.email == user_in.email)
    existing_acc = (await db.execute(email_stmt)).scalar_one_or_none()
    if existing_acc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
    # Check duplicate employee code
    if user_in.employee_code:
        code_stmt = select(UserProfile).where(
            UserProfile.tenant_id == tenant_id, 
            UserProfile.employee_code == user_in.employee_code,
            UserProfile.deleted_at.is_(None)
        )
        existing_code = (await db.execute(code_stmt)).scalar_one_or_none()
        if existing_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee code already in use")

    # 1. Create UserAccount
    new_account = UserAccount(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True
    )
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)

    # 2. Create UserProfile
    profile_data = user_in.model_dump(exclude={"email", "password", "roles"})
    db_user = UserProfile(
        **profile_data, 
        user_id=new_account.id, 
        tenant_id=tenant_id,
        created_by=uuid.UUID(current_user_id) if current_user_id else None
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # 3. Assign Roles
    for role_id in user_in.roles:
        new_user_role = TenantUserRole(
            tenant_id=tenant_id,
            user_id=db_user.id,
            role_id=role_id,
            created_by=uuid.UUID(current_user_id) if current_user_id else None
        )
        db.add(new_user_role)
    if user_in.roles:
        await db.commit()

    response_data = db_user.__dict__.copy()
    response_data["email"] = new_account.email
    return response_data

@router.get("/", response_model=List[UserProfileResponse])
async def list_users(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    department_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
):
    """List all active users with search, filter, and pagination."""
    stmt = select(UserProfile, UserAccount.email).join(
        UserAccount, UserAccount.id == UserProfile.user_id
    ).where(
        UserProfile.tenant_id == tenant_id,
        UserProfile.deleted_at.is_(None)
    )
    
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                UserProfile.first_name.ilike(search_term),
                UserProfile.last_name.ilike(search_term),
                UserProfile.employee_code.ilike(search_term),
                UserAccount.email.ilike(search_term)
            )
        )
        
    if department_id:
        stmt = stmt.where(UserProfile.department_id == department_id)
        
    if status_filter:
        if status_filter.lower() == 'active':
            stmt = stmt.where(UserProfile.is_active.is_(True))
        elif status_filter.lower() in ('inactive', 'suspended'):
            stmt = stmt.where(UserProfile.is_active.is_(False))
            
    stmt = stmt.order_by(UserProfile.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    
    users_resp = []
    for user_profile, email in result.all():
        data = user_profile.__dict__.copy()
        data["email"] = email
        users_resp.append(data)
        
    return users_resp

@router.get("/{profile_id}", response_model=UserProfileResponse)
async def get_user_profile(
    profile_id: uuid.UUID,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific user profile."""
    stmt = select(UserProfile, UserAccount.email).join(
        UserAccount, UserAccount.id == UserProfile.user_id
    ).where(
        UserProfile.id == profile_id,
        UserProfile.tenant_id == tenant_id,
        UserProfile.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    user_profile, email = row
    response_data = user_profile.__dict__.copy()
    response_data["email"] = email
    return response_data

@router.patch("/{profile_id}", response_model=UserProfileResponse)
async def update_user_profile(
    request: Request,
    profile_id: uuid.UUID,
    user_update: UserProfileUpdate,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    current_user_id = getattr(request.state, "user_id", None)
    
    stmt = select(UserProfile, UserAccount).join(
        UserAccount, UserAccount.id == UserProfile.user_id
    ).where(
        UserProfile.id == profile_id,
        UserProfile.tenant_id == tenant_id,
        UserProfile.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    db_user, user_account = row
        
    update_dict = user_update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_user, key, value)
        
    if current_user_id:
        db_user.updated_by = uuid.UUID(current_user_id)
    db_user.updated_at = datetime.now(timezone.utc)
        
    await db.commit()
    await db.refresh(db_user)
    
    response_data = db_user.__dict__.copy()
    response_data["email"] = user_account.email
    return response_data

@router.patch("/{profile_id}/status", response_model=UserProfileResponse)
async def change_user_status(
    request: Request,
    profile_id: uuid.UUID,
    is_active: bool,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Activate or suspend user."""
    return await update_user_profile(
        request=request,
        profile_id=profile_id,
        user_update=UserProfileUpdate(is_active=is_active, status="Active" if is_active else "Suspended"),
        tenant_id=tenant_id,
        db=db
    )

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    profile_id: uuid.UUID,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete user."""
    current_user_id = getattr(request.state, "user_id", None)
    
    stmt = select(UserProfile).where(
        UserProfile.id == profile_id,
        UserProfile.tenant_id == tenant_id,
        UserProfile.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    db_user.deleted_at = datetime.now(timezone.utc)
    if current_user_id:
        db_user.updated_by = uuid.UUID(current_user_id)
        
    # Optional: also disable the UserAccount
    acc_stmt = select(UserAccount).where(UserAccount.id == db_user.user_id)
    acc = (await db.execute(acc_stmt)).scalar_one_or_none()
    if acc:
        acc.is_active = False
        
    await db.commit()
    return None
