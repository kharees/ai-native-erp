import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import uuid

from app.core.config import settings
from app.models.auth import UserAccount
from app.models.users import UserProfile
from app.models.tenants import Tenant
from app.models.rbac import TenantRole, TenantUserRole
import app.models.organization  # Important for foreign keys
from app.core.security import get_password_hash

async def _ensure_super_admin_role(session: AsyncSession, tenant_id, profile_id) -> None:
    """Idempotently grant the profile a Super Admin RBAC role.

    UserProfile.role is a free-text label with no bearing on actual
    authorization - RequirePermission checks tenant_roles/tenant_user_roles
    exclusively (looking at TenantRole.is_admin_bypass, not the role name -
    see migration c6d8e0f2a4b7). Without this, the seeded admin account
    403s on every permission-gated endpoint despite UserProfile.role="admin"
    suggesting otherwise.
    """
    role_result = await session.execute(
        select(TenantRole).where(TenantRole.tenant_id == tenant_id, TenantRole.name == "Super Admin")
    )
    role = role_result.scalar_one_or_none()
    if not role:
        role = TenantRole(tenant_id=tenant_id, name="Super Admin", is_system=True, hierarchy_level=1, is_admin_bypass=True)
        session.add(role)
        await session.commit()
        await session.refresh(role)
        print(f"Created role: {role.name}")

    assignment_result = await session.execute(
        select(TenantUserRole).where(
            TenantUserRole.tenant_id == tenant_id,
            TenantUserRole.user_id == profile_id,
            TenantUserRole.role_id == role.id,
        )
    )
    if not assignment_result.scalar_one_or_none():
        session.add(TenantUserRole(tenant_id=tenant_id, user_id=profile_id, role_id=role.id))
        await session.commit()
        print("Assigned Super Admin role to admin@ainative.erp")

async def seed_admin():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if user already exists
        result = await session.execute(select(UserAccount).where(UserAccount.email == "admin@ainative.erp"))
        user = result.scalar_one_or_none()

        if user:
            print("Admin user already exists.")
            profile_result = await session.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )
            profile = profile_result.scalar_one_or_none()
            if profile:
                await _ensure_super_admin_role(session, profile.tenant_id, profile.id)
            return

        # Ensure we have a tenant
        tenant_result = await session.execute(select(Tenant).limit(1))
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            tenant = Tenant(
                name="AI Native Admin Tenant",
                slug="ainative-admin",
                plan="enterprise"
            )
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            print(f"Created Tenant: {tenant.name}")

        user = UserAccount(
            email="admin@ainative.erp",
            hashed_password=get_password_hash("password123")
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        profile = UserProfile(
            user_id=user.id,
            tenant_id=tenant.id,
            first_name="System Administrator",
            role="admin"
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        await _ensure_super_admin_role(session, tenant.id, profile.id)

        print("Admin user created successfully:")
        print("Email: admin@ainative.erp")
        print("Password: password123")

if __name__ == "__main__":
    asyncio.run(seed_admin())
