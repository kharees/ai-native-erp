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
