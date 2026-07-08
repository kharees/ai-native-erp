from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.auth import UserAccount
from app.models.users import UserProfile
from app.core.security import verify_password, create_access_token, create_refresh_token

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email", "").strip()
            password = body.get("password", "")
        except:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")
    elif "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        email = form.get("username", "").strip()
        password = form.get("password", "")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported Media Type")

    if not email or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")

    # 1. Fetch UserAccount
    stmt = select(UserAccount).where(UserAccount.email == email).where(UserAccount.is_active.is_(True))
    result = await db.execute(stmt)
    user_account = result.scalar_one_or_none()

    if not user_account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # 2. Verify Password
    if not verify_password(password, user_account.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # 3. Fetch UserProfile to get tenant_id (if any)
    prof_stmt = select(UserProfile).where(UserProfile.user_id == user_account.id).where(UserProfile.is_active.is_(True))
    prof_result = await db.execute(prof_stmt)
    user_profile = prof_result.scalar_one_or_none()

    tenant_id = None
    if user_profile:
        tenant_id = str(user_profile.tenant_id)

    # 4. Create tokens
    jwt_data = {
        "sub": str(user_account.id),
        "email": user_account.email
    }
    
    # We must match what tenant_auth.py expects. It looks at:
    # app_metadata.tenant_id or user_metadata.tenant_id or raw_tenant_id
    if tenant_id:
        jwt_data["app_metadata"] = {"tenant_id": tenant_id}

    access_token = create_access_token(data=jwt_data)
    refresh_token = create_refresh_token(data=jwt_data)

    user_info = {
        "id": str(user_account.id),
        "email": user_account.email,
        "tenant_id": tenant_id,
        "first_name": user_profile.first_name if user_profile else None,
        "last_name": user_profile.last_name if user_profile else None
    }

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_info
    )

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    from jose import jwt, JWTError
    from app.core.config import settings

    try:
        payload = jwt.decode(req.refresh_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Verify user exists
    stmt = select(UserAccount).where(UserAccount.id == uuid.UUID(user_id)).where(UserAccount.is_active.is_(True))
    result = await db.execute(stmt)
    user_account = result.scalar_one_or_none()

    if not user_account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Fetch profile
    prof_stmt = select(UserProfile).where(UserProfile.user_id == user_account.id).where(UserProfile.is_active.is_(True))
    prof_result = await db.execute(prof_stmt)
    user_profile = prof_result.scalar_one_or_none()

    tenant_id = str(user_profile.tenant_id) if user_profile else None

    jwt_data = {
        "sub": str(user_account.id),
        "email": user_account.email
    }
    if tenant_id:
        jwt_data["app_metadata"] = {"tenant_id": tenant_id}

    new_access = create_access_token(data=jwt_data)
    new_refresh = create_refresh_token(data=jwt_data)
    
    user_info = {
        "id": str(user_account.id),
        "email": user_account.email,
        "tenant_id": tenant_id,
        "first_name": user_profile.first_name if user_profile else None,
        "last_name": user_profile.last_name if user_profile else None
    }

    return TokenResponse(access_token=new_access, refresh_token=new_refresh, user=user_info)

@router.get("/me")
async def get_current_user_me(request: Request, db: AsyncSession = Depends(get_db)):
    # Since /api/v1/auth is bypassed in TenantAuthMiddleware, we must decode the token here
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    token = auth_header[len("Bearer "):]
    from jose import jwt, JWTError
    from app.core.config import settings
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    stmt = select(UserAccount).where(UserAccount.id == uuid.UUID(user_id)).where(UserAccount.is_active.is_(True))
    result = await db.execute(stmt)
    user_account = result.scalar_one_or_none()
    
    if not user_account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    prof_stmt = select(UserProfile).where(UserProfile.user_id == user_account.id).where(UserProfile.is_active.is_(True))
    prof_result = await db.execute(prof_stmt)
    user_profile = prof_result.scalar_one_or_none()
    
    return {
        "id": str(user_account.id),
        "email": user_account.email,
        "tenant_id": str(user_profile.tenant_id) if user_profile else None,
        "first_name": user_profile.first_name if user_profile else None,
        "last_name": user_profile.last_name if user_profile else None
    }

@router.post("/logout")
async def logout():
    # In a stateless JWT setup, client deletes the token.
    # Optionally, we could blacklist the token here.
    return {"message": "Logged out successfully"}
