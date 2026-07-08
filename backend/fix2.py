import os

def fix_auth_headers():
    file_path = "tests/conftest.py"
    with open(file_path, "r") as f:
        content = f.read()
        
    replacement = """from app.models.users import UserProfile

@pytest_asyncio.fixture
async def auth_headers(setup_tenant, db_session: AsyncSession):
    user_id = uuid.uuid4()
    profile = UserProfile(
        user_id=user_id,
        tenant_id=setup_tenant.id,
        first_name="Test User",
        email="test@example.com",
        is_active=True
    )
    # email might not be in the model, let's just use what's required
    # Looking at UserProfile, email is NOT there. user_id, tenant_id are required.
    profile = UserProfile(
        user_id=user_id,
        tenant_id=setup_tenant.id,
        first_name="Test User",
        is_active=True
    )
    db_session.add(profile)
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
    profile = UserProfile(
        user_id=user_id,
        tenant_id=alt_tenant.id,
        first_name="Alt User",
        is_active=True
    )
    db_session.add(profile)
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
"""

    import re
    # We will replace everything from `@pytest_asyncio.fixture` of `auth_headers` to the end of the file
    content = re.sub(r'@pytest_asyncio\.fixture\nasync def auth_headers.*', replacement, content, flags=re.DOTALL)
    
    with open(file_path, "w") as f:
        f.write(content)

if __name__ == "__main__":
    fix_auth_headers()
