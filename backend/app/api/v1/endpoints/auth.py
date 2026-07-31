import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.auth import UserAccount
from app.models.users import UserProfile
from app.models.sessions import TenantSession
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

router = APIRouter()

# The refresh token is never sent to JS — see TokenResponse.refresh_token's
# docstring below. Scoped to /api/v1/auth (only the routes that need it:
# /refresh reads it, /logout clears it) rather than the whole site, so it
# isn't attached to every unrelated API request.
_REFRESH_COOKIE_NAME = "refresh_token"
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=_REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)


# Precomputed once at import time so an unknown-email login still pays the
# same bcrypt.checkpw() cost as a known-email login with the wrong
# password — otherwise "unknown email" returns fast (no bcrypt call) and
# "known email, wrong password" returns slow, letting an attacker
# enumerate valid emails purely from response timing.
_DUMMY_PASSWORD_HASH = get_password_hash("timing-parity-dummy-password")


class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    # Deliberately never populated — the refresh token travels only via the
    # httpOnly `refresh_token` cookie set on /login and /refresh, never in a
    # JSON body a script can read. Kept as a field (always null) rather than
    # removed outright so any code still destructuring res.data.refresh_token
    # gets `undefined`/`null` instead of a hard KeyError. See #10 in the
    # audit: tokens in localStorage are fully exposed to any XSS anywhere in
    # the app; an httpOnly cookie is invisible to JS entirely.
    refresh_token: None = None
    token_type: str = "bearer"
    user: dict

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/15minutes")
async def login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email", "").strip()
            password = body.get("password", "")
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
            # JSONDecodeError: malformed JSON. AttributeError: valid JSON
            # that isn't an object (e.g. a bare array/string/number, so
            # .get() doesn't exist). A bare `except:` here previously also
            # swallowed CancelledError (breaking request cancellation/
            # shutdown) and any other unrelated exception, masking real bugs.
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
        # Same bcrypt comparison cost as the "found" path below, even
        # though this is guaranteed to fail — closes the timing
        # side-channel (audit #4) without changing the response.
        verify_password(password, _DUMMY_PASSWORD_HASH)
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
        await db.flush()
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

    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        user=user_info
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from jose import jwt, JWTError

    incoming_refresh_token = request.cookies.get(_REFRESH_COOKIE_NAME)
    if not incoming_refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token cookie present")

    try:
        payload = jwt.decode(incoming_refresh_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
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

    if not user_profile:
        # Never silently mint a tenant-less access token here -- unlike
        # /auth/login (which fails the same way), this endpoint is called
        # automatically on every page load via bootstrapAuth(), so a silent
        # None would turn into "No tenant_id claim found" 403s across the
        # entire app instead of a clean prompt to log back in.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to resolve tenant for this session. Please log in again.",
        )

    tenant_id = str(user_profile.tenant_id)

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
        "email": user_account.email,
        "app_metadata": {"tenant_id": tenant_id},
    }
    if session_id:
        jwt_data["session_id"] = session_id

    new_access = create_access_token(data=jwt_data)
    new_refresh = create_refresh_token(data=jwt_data)

    user_info = {
        "id": str(user_account.id),
        "email": user_account.email,
        "tenant_id": tenant_id,
        "first_name": user_profile.first_name,
        "last_name": user_profile.last_name
    }

    # Rotate the cookie on every refresh (new refresh token, new expiry).
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access, user=user_info)

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
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Revoke the calling token's session (if any) so it can no longer pass
    TenantAuthMiddleware's session-active check, and clear the refresh
    cookie so the browser can't silently mint a new access token after
    logout."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        from jose import jwt, JWTError
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            session_id = payload.get("session_id")
            if session_id:
                stmt = select(TenantSession).where(TenantSession.id == uuid.UUID(session_id))
                result = await db.execute(stmt)
                session_obj = result.scalar_one_or_none()
                if session_obj:
                    session_obj.is_active = False
                    await db.flush()
        except JWTError:
            pass

    _clear_refresh_cookie(response)
    return {"message": "Logged out successfully"}
