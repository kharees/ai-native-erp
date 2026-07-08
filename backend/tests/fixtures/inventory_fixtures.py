import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import uuid
from main import app
from app.core.database import Base
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import TestingSessionLocal
from app.models.tenants import Tenant
import datetime
from datetime import timezone

# Mock JWT for generating tokens
from jose import jwt
from app.core.config import settings

def create_mock_token(tenant_id: str, user_id: str, scopes: list[str]) -> str:
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "scopes": scopes,
        "exp": datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=30)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

@pytest_asyncio.fixture
async def setup_tenant(db_session: AsyncSession):
    tenant = Tenant(name="Test Tenant", slug="test", plan="enterprise")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant

@pytest_asyncio.fixture
async def auth_headers(setup_tenant):
    token = create_mock_token(
        tenant_id=str(setup_tenant.id),
        user_id=str(uuid.uuid4()),
        scopes=[
            "UniversalInventory:MasterData:Read",
            "UniversalInventory:MasterData:Create",
            "UniversalInventory:Stock:Update",
            "UniversalInventory:Ledger:Read",
            "UniversalInventory:Tracking:Read",
            "UniversalInventory:Tracking:Create",
            "UniversalInventory:Reports:Read",
            "UniversalInventory:Intelligence:Read"
        ]
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup_tenant.id)}

@pytest_asyncio.fixture
async def alt_tenant_headers(db_session: AsyncSession):
    # Tests multi-tenant isolation
    tenant = Tenant(name="Alt Tenant", slug="alt", plan="enterprise")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    token = create_mock_token(
        tenant_id=str(tenant.id),
        user_id=str(uuid.uuid4()),
        scopes=["UniversalInventory:MasterData:Read", "UniversalInventory:MasterData:Create"]
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}
