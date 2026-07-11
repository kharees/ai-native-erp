"""
app/api/v1/endpoints/tenants.py
===============================
Router for multi-tenant administration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.tenants import Tenant
from app.middleware.tenant_auth import TenantIDDep

router = APIRouter()

# NOTE: /me is intentionally left authentication-only (no RequirePermission
# gate). It only ever returns the caller's own tenant's public profile —
# every authenticated member of a tenant is expected to be able to read
# their own tenant's name/plan (e.g. for display in the app header).
# Gating a self-read endpoint behind a granular permission would silently
# 403 ordinary staff roles that have no explicit grant for it yet.
@router.get("/me")
async def get_current_tenant(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db)
):
    """Get details of the currently authenticated tenant."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at,
    }
