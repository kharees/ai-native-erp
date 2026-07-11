from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.auth import UserAccount
from app.models.users import UserProfile
from app.models.sessions import TenantSession
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

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

    # 4. Create a tracked session row (enables real revocation — see
    #    TenantAuthMiddleware's session-active check and DELETE /sessions/*).
    #    Only tenant-scoped users get a session; tenant-less accounts fall
    #    back to plain stateless JWTs as before.
    session_id: str | None = None
    if user_profile:
        now = datetime.now(timezone.utc)
        ua_header = (request.headers.get("user-agent") or "")[:64]
        new_session = TenantSession(
            tenant_id=user_profile.tenant_id,
            user_id=user_profile.id,
            ip_address=request.client.host if request.client else None,
            browser=ua_header or None,
            is_active=True,
            last_active_at=now,
            expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        session_id = str(new_session.id)

    # 5. Create tokens
    jwt_data = {
        "sub": str(user_account.id),
        "email": user_account.email
    }

    # We must match what tenant_auth.py expects. It looks at:
    # app_metadata.tenant_id or user_metadata.tenant_id or raw_tenant_id
    if tenant_id:
        jwt_data["app_metadata"] = {"tenant_id": tenant_id}
    if session_id:
        jwt_data["session_id"] = session_id

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
        # Reject access tokens presented at the refresh endpoint — access and
        # refresh tokens share a secret, so the type claim is the only thing
        # stopping one from being replayed as the other.
        if payload.get("token_type") != "refresh":
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

    # Carry the session_id forward so a revoked session cannot be resurrected
    # by refreshing — a refresh token minted before revocation must not be
    # able to mint a fresh, unrevoked-looking access token.
    session_id = payload.get("session_id")
    if session_id:
        sess_stmt = select(TenantSession.is_active).where(TenantSession.id == uuid.UUID(session_id))
        sess_result = await db.execute(sess_stmt)
        session_active = sess_result.scalar_one_or_none()
        if session_active is not True:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked. Please log in again.")

    jwt_data = {
        "sub": str(user_account.id),
        "email": user_account.email
    }
    if tenant_id:
        jwt_data["app_metadata"] = {"tenant_id": tenant_id}
    if session_id:
        jwt_data["session_id"] = session_id

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
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Revoke the calling token's session (if any) so it can no longer pass
    TenantAuthMiddleware's session-active check, in addition to the client
    discarding the token locally."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        from jose import jwt, JWTError
        from app.core.config import settings
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            session_id = payload.get("session_id")
            if session_id:
                stmt = select(TenantSession).where(TenantSession.id == uuid.UUID(session_id))
                result = await db.execute(stmt)
                session_obj = result.scalar_one_or_none()
                if session_obj:
                    session_obj.is_active = False
                    await db.commit()
        except JWTError:
            pass

    return {"message": "Logged out successfully"}
