import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import uuid

from app.core.config import settings
from app.models.auth import UserAccount
from app.models.users import UserProfile
from app.models.tenants import Tenant
import app.models.organization  # Important for foreign keys
from app.core.security import get_password_hash

async def seed_admin():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if user already exists
        result = await session.execute(select(UserAccount).where(UserAccount.email == "admin@ainative.erp"))
        user = result.scalar_one_or_none()
        
        if user:
            print("Admin user already exists.")
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
        
        print("Admin user created successfully:")
        print("Email: admin@ainative.erp")
        print("Password: password123")

if __name__ == "__main__":
    asyncio.run(seed_admin())
