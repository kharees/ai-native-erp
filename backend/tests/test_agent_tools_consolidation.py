"""
tests/test_agent_tools_consolidation.py
==========================================
Covers the 5-copilot consolidation (app/agent/orchestrator/loop.py's
get_tools_for_user): tools from every registered module (billing, finance,
inventory, migration, security, analytics) are merged, then filtered
per-request by the caller's real RBAC permissions BEFORE the list is ever
sent to the model -- a user without a module's permissions doesn't just
get blocked at dispatch time, they never see that module's tools as an
option at all.

Real database, real RBAC (TenantPermission/TenantRolePermission/
TenantUserRole), same _make_tenant_and_user helper pattern as
tests/test_orchestrator.py.
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from app.agent.orchestrator.loop import _ALL_TOOL_MODULES, get_tools_for_user
from app.core.database import db_session
from app.middleware.rbac import _clear_permission_cache
from app.models.auth import UserAccount
from app.models.rbac import TenantPermission, TenantRole, TenantRolePermission, TenantUserRole
from app.models.tenants import Tenant
from app.models.users import UserProfile

pytestmark = pytest.mark.asyncio

_ALL_BILLING_PERMISSIONS = [
    ("UniversalBilling", "Invoices", "Create"),
    ("UniversalBilling", "Payments", "Create"),
    ("UniversalBilling", "Customers", "Read"),
]


async def _make_tenant_and_user(permissions: list[tuple[str, str, str]]) -> tuple[uuid.UUID, uuid.UUID]:
    _clear_permission_cache()
    async with db_session() as db:
        tenant = Tenant(name="Consolidation Test", slug=f"consol-{uuid.uuid4().hex[:10]}", plan="enterprise")
        db.add(tenant)
        await db.flush()

        user_id = uuid.uuid4()
        db.add(UserAccount(id=user_id, email=f"{user_id}@example.com", hashed_password="x", is_active=True))
        await db.flush()

        profile = UserProfile(user_id=user_id, tenant_id=tenant.id, first_name="Consolidation Test User", is_active=True)
        db.add(profile)
        await db.flush()

        if permissions:
            role = TenantRole(tenant_id=tenant.id, name="Consolidation Test Role", is_system=False, hierarchy_level=100)
            db.add(role)
            await db.flush()
            for module, feature, action in permissions:
                # TenantPermission is a global catalog table (no tenant_id,
                # unique on (module, feature, action)) -- get-or-create
                # rather than blind-insert; see test_orchestrator.py's
                # identical helper for the full rationale.
                perm = (await db.execute(
                    select(TenantPermission).where(
                        TenantPermission.module == module,
                        TenantPermission.feature == feature,
                        TenantPermission.action == action,
                    )
                )).scalar_one_or_none()
                if perm is None:
                    perm = TenantPermission(module=module, feature=feature, action=action)
                    db.add(perm)
                    await db.flush()
                db.add(TenantRolePermission(role_id=role.id, permission_id=perm.id, conditions={}))
                await db.flush()
            db.add(TenantUserRole(tenant_id=tenant.id, user_id=profile.id, role_id=role.id))

        return tenant.id, user_id


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(TenantUserRole).where(TenantUserRole.tenant_id == tenant_id))
        await db.execute(delete(TenantRolePermission).where(
            TenantRolePermission.role_id.in_(select(TenantRole.id).where(TenantRole.tenant_id == tenant_id))
        ))
        await db.execute(delete(TenantRole).where(TenantRole.tenant_id == tenant_id))
        await db.execute(delete(UserProfile).where(UserProfile.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


def _all_registered_tool_names() -> set[str]:
    return {t.name for module in _ALL_TOOL_MODULES for t in module}


async def test_user_without_finance_permissions_does_not_receive_finance_tools():
    """The explicit ask: a user who only has Billing permissions must not
    see get_finance_insights (required_permission=("Finance", "AICopilot",
    "Read")) in their available tool list -- not filtered out at dispatch
    time, never proposed to the model in the first place."""
    tenant_id, user_id = await _make_tenant_and_user(_ALL_BILLING_PERMISSIONS)
    try:
        async with db_session() as db:
            tools = await get_tools_for_user(tenant_id, user_id, db)

        tool_names = {t.name for t in tools}
        assert "get_finance_insights" not in tool_names

        # Positive control: the permissions this user DOES have really do
        # grant billing tools -- proves the filter isn't just blocking
        # everything (which would make the finance assertion meaningless).
        assert "create_invoice" in tool_names
        assert "search_customer" in tool_names
    finally:
        await _cleanup(tenant_id)


async def test_user_with_finance_permissions_receives_finance_tools():
    tenant_id, user_id = await _make_tenant_and_user([("Finance", "AICopilot", "Read")])
    try:
        async with db_session() as db:
            tools = await get_tools_for_user(tenant_id, user_id, db)

        tool_names = {t.name for t in tools}
        assert "get_finance_insights" in tool_names
        # And this user has no billing permissions -- proves the filter is
        # a real per-tool RBAC check, not an all-or-nothing tenant flag.
        assert "create_invoice" not in tool_names
    finally:
        await _cleanup(tenant_id)


async def test_user_with_no_permissions_receives_no_tools():
    tenant_id, user_id = await _make_tenant_and_user([])
    try:
        async with db_session() as db:
            tools = await get_tools_for_user(tenant_id, user_id, db)
        assert tools == []
    finally:
        await _cleanup(tenant_id)


async def test_all_six_tool_modules_are_merged_and_reachable():
    """Every module registered in _ALL_TOOL_MODULES is actually included
    in the merge -- a user with every module's permission sees every tool,
    not just a subset the merge silently dropped."""
    all_permissions = sorted({tool.required_permission for module in _ALL_TOOL_MODULES for tool in module})
    tenant_id, user_id = await _make_tenant_and_user(list(all_permissions))
    try:
        async with db_session() as db:
            tools = await get_tools_for_user(tenant_id, user_id, db)

        assert {t.name for t in tools} == _all_registered_tool_names()
    finally:
        await _cleanup(tenant_id)
