from datetime import datetime, timezone, timedelta
"""
tests/conftest.py
=================
Pytest configuration and global asynchronous fixtures.
Provides an isolated, transactional database for each test and a mock FastAPI client.
"""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi import Request

# Mock JWT before importing the app
from jose import jwt

# Application imports
from app.core.database import Base, get_db
import app.core.database as db

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/universal_ai_erp"
from sqlalchemy.pool import NullPool
engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Mock it GLOBALLY before any other module imports it
db.engine = engine
db.AsyncSessionLocal = TestingSessionLocal

from main import app
from app.core.config import settings
import app.middleware.tenant_auth as tenant_auth_mod
from app.middleware.rbac import RequirePermission
from app.models.tenants import Tenant



@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    res = policy.new_event_loop()
    asyncio.set_event_loop(res)
    res._close = res.close
    res.close = lambda: None
    yield res
    res._close()

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields an AsyncSession using SQLite memory db."""
    import pkgutil
    import importlib
    import app.models
    for _, module_name, _ in pkgutil.walk_packages(app.models.__path__):
        try:
            importlib.import_module(f"app.models.{module_name}")
        except Exception:
            pass
    


    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    connection = await engine.connect()
    transaction = await connection.begin()
    
    session = TestingSessionLocal(bind=connection)
    yield session
    
    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def mock_async_session_local():
        print("MOCK ASYNC SESSION LOCAL CALLED!")
        yield db_session
            
    original_session_local = tenant_auth_mod.AsyncSessionLocal
    tenant_auth_mod.AsyncSessionLocal = mock_async_session_local
    
    # Mock RequirePermission for tests
    original_require_permission = RequirePermission.__call__
    
    async def mock_require_permission_call(self, request: Request, db=None):
        return True
        
    RequirePermission.__call__ = mock_require_permission_call
    
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://localhost"
    ) as ac:
        yield ac
        
    app.dependency_overrides.clear()
    tenant_auth_mod.AsyncSessionLocal = original_session_local
    RequirePermission.__call__ = original_require_permission

def create_mock_token(tenant_id: str, user_id: str, scopes: list[str]) -> str:
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "scopes": scopes,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def mock_jwt():
    """Factory fixture building a JWT matching TenantAuthMiddleware's expected claim shape
    (tenant_id under app_metadata, optional session_id/jti for session-bound tests)."""
    def _make(sub: str, tenant_id: str, session_id: str | None = None, scopes: list[str] | None = None) -> str:
        payload = {
            "sub": sub,
            "app_metadata": {"tenant_id": tenant_id},
            "scopes": scopes or [],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        if session_id:
            payload["session_id"] = session_id
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return _make


@pytest_asyncio.fixture
async def setup_tenant(db_session: AsyncSession):
    tenant = Tenant(name="Test Tenant", slug="test", plan="enterprise")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant

from app.models.users import UserProfile
from app.models.auth import UserAccount

@pytest_asyncio.fixture
async def auth_headers(setup_tenant, db_session: AsyncSession):
    user_id = uuid.uuid4()
    account = UserAccount(
        id=user_id,
        email=f"{user_id}@test.local",
        hashed_password="not-a-real-hash",
        is_active=True
    )
    profile = UserProfile(
        user_id=user_id,
        tenant_id=setup_tenant.id,
        first_name="Test User",
        is_active=True
    )
    db_session.add_all([account, profile])
    await db_session.commit()
    
    token = create_mock_token(
        tenant_id=str(setup_tenant.id),
        user_id=str(user_id),
        scopes=[
            "UniversalInventory:MasterData:Read",
            "UniversalInventory:MasterData:Create",
            "UniversalInventory:Stock:Update",
            "UniversalInventory:Ledger:Read",
            "UniversalInventory:Tracking:Read",
            "UniversalInventory:Tracking:Create",
            "UniversalInventory:Reports:Read",
            "UniversalInventory:Intelligence:Read",
            "FinanceCore:AccountGroups:Create",
            "FinanceCore:AccountGroups:Read",
            "FinanceCore:AccountGroups:Update",
            "FinanceCore:Accounts:Create",
            "FinanceCore:Accounts:Read",
            "FinanceCore:Journal:Create",
            "FinanceCore:Journal:Read",
            "FinanceAR:Ledger:Create",
            "FinanceAR:Ledger:Read",
            "FinanceAP:Vendors:Create",
            "FinanceAP:Vendors:Read",
            "FinanceAP:Bills:Create",
            "FinanceAP:Payments:Create",
            "FinanceBanking:Accounts:Read",
            "FinanceBanking:Reconciliation:Create",
            "FinanceAssets:Categories:Create",
            "FinanceAssets:Assets:Create",
            "FinanceAssets:Depreciation:Create",
            "FinanceBudget:Budgets:Create",
            "FinanceBudget:Forecasts:Create",
            "FinanceReports:TrialBalance:Read",
            "FinanceReports:ProfitLoss:Read",
            "FinanceReports:BalanceSheet:Read",
            "FinanceReports:CashFlow:Read",
            "FinanceAI:Insights:Read",
            "FinanceAI:Copilot:Create",
            "FinanceAI:Fraud:Create"
        ]
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup_tenant.id)}

@pytest_asyncio.fixture
async def alt_tenant_headers(db_session: AsyncSession):
    alt_tenant = Tenant(name="Alt Tenant", slug="alt", plan="enterprise")
    db_session.add(alt_tenant)
    await db_session.commit()
    await db_session.refresh(alt_tenant)
    
    user_id = uuid.uuid4()
    account = UserAccount(
        id=user_id,
        email=f"{user_id}@test.local",
        hashed_password="not-a-real-hash",
        is_active=True
    )
    profile = UserProfile(
        user_id=user_id,
        tenant_id=alt_tenant.id,
        first_name="Alt User",
        is_active=True
    )
    db_session.add_all([account, profile])
    await db_session.commit()
    
    token = create_mock_token(
        tenant_id=str(alt_tenant.id),
        user_id=str(user_id),
        scopes=[
            "UniversalInventory:MasterData:Create",
            "UniversalInventory:Stock:Update",
            "UniversalInventory:Ledger:Read",
            "UniversalInventory:Tracking:Read",
            "UniversalInventory:Tracking:Create",
            "UniversalInventory:Reports:Read",
            "UniversalInventory:Intelligence:Read",
            "FinanceCore:AccountGroups:Create",
            "FinanceCore:AccountGroups:Read",
            "FinanceCore:AccountGroups:Update",
            "FinanceCore:Accounts:Create",
            "FinanceCore:Accounts:Read",
            "FinanceCore:Journal:Create",
            "FinanceCore:Journal:Read",
            "FinanceAR:Ledger:Create",
            "FinanceAR:Ledger:Read",
            "FinanceAP:Vendors:Create",
            "FinanceAP:Vendors:Read",
            "FinanceAP:Bills:Create",
            "FinanceAP:Payments:Create",
            "FinanceBanking:Accounts:Read",
            "FinanceBanking:Reconciliation:Create",
            "FinanceAssets:Categories:Create",
            "FinanceAssets:Assets:Create",
            "FinanceAssets:Depreciation:Create",
            "FinanceBudget:Budgets:Create",
            "FinanceBudget:Forecasts:Create",
            "FinanceReports:TrialBalance:Read",
            "FinanceReports:ProfitLoss:Read",
            "FinanceReports:BalanceSheet:Read",
            "FinanceReports:CashFlow:Read",
            "FinanceAI:Insights:Read",
            "FinanceAI:Copilot:Create",
            "FinanceAI:Fraud:Create"
        ]
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(alt_tenant.id)}
