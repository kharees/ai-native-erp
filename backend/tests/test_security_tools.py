"""
tests/test_security_tools.py
===============================
Coverage for app/agent/tools/security_tools.py -- previously had zero
test references anywhere in the suite (verified by direct grep, not just
a missing _schemas.py file). Combines the three patterns already
established across the other tool modules' test files into one file
(the module is small -- two tools -- so a single file is proportionate;
mirrors tests/test_analytics_tool_schemas.py + tests/test_analytics_tools.py
+ tests/test_agent_tools_consolidation.py's RBAC-gating pattern):

  1. Schema/handler consistency (assert_tool_schema_matches_handler,
     tests/agent_tool_schema_checks.py).
  2. Real behavior against seeded data -- no LLM, no orchestrator --
     app.core.database.db_session() directly, same as
     tests/test_analytics_tools.py.
  3. RBAC permission gating -- a user without the tool's
     required_permission does not receive it from get_tools_for_user,
     same pattern as tests/test_agent_tools_consolidation.py.

No confirmation-gating section: both tools are read-only (neither
mutates state), and the schema-consistency section below asserts
requires_confirmation is False for both -- ToolDefinition's own docstring
says that gate exists only for tools that mutate real state, which
neither of these does.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select

from app.agent.orchestrator.loop import get_tools_for_user
from app.agent.tools.security_tools import SECURITY_TOOLS, handle_get_inactive_users, handle_get_org_risk_score
from app.core.database import db_session
from app.middleware.rbac import _clear_permission_cache
from app.models.audit import TenantAuditLog
from app.models.auth import UserAccount
from app.models.rbac import TenantPermission, TenantRole, TenantRolePermission, TenantUserRole
from app.models.sessions import TenantSession
from app.models.tenants import Tenant
from app.models.users import UserProfile
from tests.agent_tool_schema_checks import assert_tool_schema_matches_handler

# No module-level `pytestmark = pytest.mark.asyncio` here (unlike e.g.
# test_analytics_tools.py) -- this file mixes sync schema-consistency
# tests with async behavior/RBAC tests, and pytest.ini's asyncio_mode =
# auto already detects async def tests without any marker needed.

# Both security tools only ever get tenant_id injected by the orchestrator
# -- neither takes a user_id/idempotency_key (read-only, nothing to retry
# safely or attribute to an actor).
_INJECTED_PARAMS = {"tenant_id"}


def _tool_def(name: str):
    return next(t for t in SECURITY_TOOLS if t.name == name)


# ---------------------------------------------------------------------
# 1. Schema/handler consistency + confirmation-gating
# ---------------------------------------------------------------------

@pytest.mark.parametrize("tool_name", ["get_inactive_users", "get_org_risk_score"])
def test_tool_schema_fields_match_real_handler_parameters(tool_name):
    assert_tool_schema_matches_handler(_tool_def(tool_name), injected_params=_INJECTED_PARAMS)


@pytest.mark.parametrize("tool", SECURITY_TOOLS)
def test_no_security_tool_requires_confirmation(tool):
    """Both tools are read-only -- neither mutates tenant state, so
    neither should pause the orchestrator loop for human confirmation
    (see ToolDefinition.requires_confirmation's own docstring)."""
    assert tool.requires_confirmation is False


def test_get_inactive_users_permission_is_rbac_roles_read():
    assert _tool_def("get_inactive_users").required_permission == ("RBAC", "Roles", "Read")


def test_get_org_risk_score_permission_is_audit_logs_read():
    assert _tool_def("get_org_risk_score").required_permission == ("Audit", "Logs", "Read")


# ---------------------------------------------------------------------
# 2. Real behavior against seeded data
# ---------------------------------------------------------------------

async def _make_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(name="Security Tools Test", slug=f"security-tools-{uuid.uuid4().hex[:10]}", plan="enterprise")
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant.id


async def _make_user_profile(tenant_id: uuid.UUID, *, is_active: bool = True, name: str = "Test User") -> uuid.UUID:
    async with db_session() as db:
        account_id = uuid.uuid4()
        db.add(UserAccount(id=account_id, email=f"{account_id}@example.com", hashed_password="x", is_active=True))
        await db.flush()
        profile = UserProfile(user_id=account_id, tenant_id=tenant_id, first_name=name, is_active=is_active)
        db.add(profile)
        await db.flush()
        await db.refresh(profile)
        return profile.id


async def _make_session(user_profile_id: uuid.UUID, tenant_id: uuid.UUID, last_active_at: datetime) -> None:
    async with db_session() as db:
        db.add(TenantSession(
            tenant_id=tenant_id, user_id=user_profile_id, last_active_at=last_active_at,
            expires_at=last_active_at + timedelta(days=7),
        ))
        await db.flush()


async def _make_audit_log(tenant_id: uuid.UUID, action_type: str, created_at: datetime) -> None:
    async with db_session() as db:
        db.add(TenantAuditLog(
            tenant_id=tenant_id, action_category="TEST", action_type=action_type, created_at=created_at,
        ))
        await db.flush()


async def _cleanup(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(TenantAuditLog).where(TenantAuditLog.tenant_id == tenant_id))
        await db.execute(delete(TenantSession).where(TenantSession.tenant_id == tenant_id))
        profile_ids = (await db.execute(select(UserProfile.id).where(UserProfile.tenant_id == tenant_id))).scalars().all()
        account_ids = (await db.execute(select(UserProfile.user_id).where(UserProfile.tenant_id == tenant_id))).scalars().all()
        await db.execute(delete(UserProfile).where(UserProfile.tenant_id == tenant_id))
        if account_ids:
            await db.execute(delete(UserAccount).where(UserAccount.id.in_(account_ids)))
        await db.execute(delete(TenantUserRole).where(TenantUserRole.tenant_id == tenant_id))
        await db.execute(delete(TenantRolePermission).where(
            TenantRolePermission.role_id.in_(select(TenantRole.id).where(TenantRole.tenant_id == tenant_id))
        ))
        await db.execute(delete(TenantRole).where(TenantRole.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_get_inactive_users_excludes_recently_active_user():
    tenant_id = await _make_tenant()
    try:
        profile_id = await _make_user_profile(tenant_id, name="Recently Active")
        await _make_session(profile_id, tenant_id, datetime.now(timezone.utc) - timedelta(days=1))

        result = await handle_get_inactive_users(tenant_id=tenant_id, days_inactive=30)

        assert result["total"] == 0
        assert result["inactive_users"] == []
    finally:
        await _cleanup(tenant_id)


async def test_get_inactive_users_includes_user_past_cutoff_with_iso_timestamp():
    tenant_id = await _make_tenant()
    try:
        profile_id = await _make_user_profile(tenant_id, name="Stale Session")
        stale_at = datetime.now(timezone.utc) - timedelta(days=45)
        await _make_session(profile_id, tenant_id, stale_at)

        result = await handle_get_inactive_users(tenant_id=tenant_id, days_inactive=30)

        assert result["total"] == 1
        row = result["inactive_users"][0]
        assert row["user_id"] == str(profile_id)
        assert row["name"] == "Stale Session"
        assert row["last_active"] == stale_at.isoformat()
        assert row["reason"] == "Inactive for > 30 days"
    finally:
        await _cleanup(tenant_id)


async def test_get_inactive_users_never_logged_in_reports_never():
    tenant_id = await _make_tenant()
    try:
        profile_id = await _make_user_profile(tenant_id, name="No Session Ever")
        # No _make_session call at all -- this user has zero session rows.

        result = await handle_get_inactive_users(tenant_id=tenant_id, days_inactive=30)

        assert result["total"] == 1
        assert result["inactive_users"][0]["user_id"] == str(profile_id)
        assert result["inactive_users"][0]["last_active"] == "Never"
    finally:
        await _cleanup(tenant_id)


async def test_get_inactive_users_uses_most_recent_of_multiple_sessions():
    """A user with an old AND a recent session must be judged by the
    recent one (ORDER BY last_active_at DESC LIMIT 1), not whichever
    session happens to be inserted first."""
    tenant_id = await _make_tenant()
    try:
        profile_id = await _make_user_profile(tenant_id, name="Multi Session")
        await _make_session(profile_id, tenant_id, datetime.now(timezone.utc) - timedelta(days=90))
        await _make_session(profile_id, tenant_id, datetime.now(timezone.utc) - timedelta(days=1))

        result = await handle_get_inactive_users(tenant_id=tenant_id, days_inactive=30)

        assert result["total"] == 0
    finally:
        await _cleanup(tenant_id)


async def test_get_inactive_users_excludes_inactive_user_profile():
    """is_active=False profiles are excluded entirely, regardless of
    session history -- a deactivated account isn't a "this person might
    have gone quiet" signal, it's already handled."""
    tenant_id = await _make_tenant()
    try:
        profile_id = await _make_user_profile(tenant_id, is_active=False, name="Deactivated")
        # No session -- would otherwise qualify as "Never" active.

        result = await handle_get_inactive_users(tenant_id=tenant_id, days_inactive=30)

        assert result["total"] == 0
        assert all(row["user_id"] != str(profile_id) for row in result["inactive_users"])
    finally:
        await _cleanup(tenant_id)


async def test_get_inactive_users_respects_custom_days_inactive():
    tenant_id = await _make_tenant()
    try:
        profile_id = await _make_user_profile(tenant_id, name="Ten Days Idle")
        await _make_session(profile_id, tenant_id, datetime.now(timezone.utc) - timedelta(days=10))

        # Not inactive at the default 30-day threshold...
        default_result = await handle_get_inactive_users(tenant_id=tenant_id, days_inactive=30)
        assert default_result["total"] == 0

        # ...but is inactive at an explicit, tighter 5-day threshold.
        tight_result = await handle_get_inactive_users(tenant_id=tenant_id, days_inactive=5)
        assert tight_result["total"] == 1
        assert tight_result["inactive_users"][0]["reason"] == "Inactive for > 5 days"
    finally:
        await _cleanup(tenant_id)


async def test_get_inactive_users_does_not_leak_across_tenants():
    tenant_a = await _make_tenant()
    tenant_b = await _make_tenant()
    try:
        profile_b = await _make_user_profile(tenant_b, name="Belongs To B")
        # No session for tenant B's user -- would show up as "Never" if
        # tenant isolation were broken.

        result = await handle_get_inactive_users(tenant_id=tenant_a, days_inactive=30)

        assert result["total"] == 0
        assert all(row["user_id"] != str(profile_b) for row in result["inactive_users"])
    finally:
        await _cleanup(tenant_a)
        await _cleanup(tenant_b)


async def test_get_org_risk_score_no_incidents_is_perfect_stable_score():
    tenant_id = await _make_tenant()
    try:
        result = await handle_get_org_risk_score(tenant_id=tenant_id)

        assert result == {"score": 100, "trend": "stable", "active_incidents": []}
    finally:
        await _cleanup(tenant_id)


async def test_get_org_risk_score_moderate_brute_force_docks_five_no_incident_text():
    """11-50 LOGIN_FAILED events in 24h: -5 penalty, but the incident
    message is only added above 50 -- the moderate band is silent, and
    95 >= 90 keeps trend "stable" even though the score moved."""
    tenant_id = await _make_tenant()
    try:
        now = datetime.now(timezone.utc)
        for _ in range(15):
            await _make_audit_log(tenant_id, "LOGIN_FAILED", now)

        result = await handle_get_org_risk_score(tenant_id=tenant_id)

        assert result["score"] == 95
        assert result["trend"] == "stable"
        assert result["active_incidents"] == []
    finally:
        await _cleanup(tenant_id)


async def test_get_org_risk_score_heavy_brute_force_docks_twenty_with_incident_and_decreasing_trend():
    tenant_id = await _make_tenant()
    try:
        now = datetime.now(timezone.utc)
        for _ in range(60):
            await _make_audit_log(tenant_id, "LOGIN_FAILED", now)

        result = await handle_get_org_risk_score(tenant_id=tenant_id)

        assert result["score"] == 80
        assert result["trend"] == "decreasing"
        assert len(result["active_incidents"]) == 1
        assert "brute force" in result["active_incidents"][0].lower()
    finally:
        await _cleanup(tenant_id)


async def test_get_org_risk_score_privilege_escalation_docks_fifteen_with_incident():
    tenant_id = await _make_tenant()
    try:
        now = datetime.now(timezone.utc)
        for _ in range(15):
            await _make_audit_log(tenant_id, "ROLE_ASSIGNED", now)

        result = await handle_get_org_risk_score(tenant_id=tenant_id)

        assert result["score"] == 85
        assert result["trend"] == "decreasing"
        assert len(result["active_incidents"]) == 1
        assert "privilege escalation" in result["active_incidents"][0].lower()
    finally:
        await _cleanup(tenant_id)


async def test_get_org_risk_score_combines_both_penalties():
    tenant_id = await _make_tenant()
    try:
        now = datetime.now(timezone.utc)
        for _ in range(60):
            await _make_audit_log(tenant_id, "LOGIN_FAILED", now)
        for _ in range(15):
            await _make_audit_log(tenant_id, "ROLE_ASSIGNED", now)

        result = await handle_get_org_risk_score(tenant_id=tenant_id)

        assert result["score"] == 65  # 100 - 20 - 15
        assert result["trend"] == "decreasing"
        assert len(result["active_incidents"]) == 2
    finally:
        await _cleanup(tenant_id)


async def test_get_org_risk_score_ignores_events_outside_24h_window():
    tenant_id = await _make_tenant()
    try:
        stale = datetime.now(timezone.utc) - timedelta(days=2)
        for _ in range(60):
            await _make_audit_log(tenant_id, "LOGIN_FAILED", stale)

        result = await handle_get_org_risk_score(tenant_id=tenant_id)

        assert result["score"] == 100
        assert result["active_incidents"] == []
    finally:
        await _cleanup(tenant_id)


async def test_get_org_risk_score_does_not_leak_across_tenants():
    tenant_a = await _make_tenant()
    tenant_b = await _make_tenant()
    try:
        now = datetime.now(timezone.utc)
        for _ in range(60):
            await _make_audit_log(tenant_b, "LOGIN_FAILED", now)

        result = await handle_get_org_risk_score(tenant_id=tenant_a)

        assert result["score"] == 100
        assert result["active_incidents"] == []
    finally:
        await _cleanup(tenant_a)
        await _cleanup(tenant_b)


# ---------------------------------------------------------------------
# 3. RBAC permission gating
# ---------------------------------------------------------------------

async def _make_tenant_and_user(permissions: list[tuple[str, str, str]]) -> tuple[uuid.UUID, uuid.UUID]:
    """Same pattern as tests/test_agent_tools_consolidation.py's helper of
    the same name -- returns (tenant_id, user_account_id), not a
    UserProfile id, since get_tools_for_user takes the account id (same
    as the JWT's `sub`)."""
    _clear_permission_cache()
    async with db_session() as db:
        tenant = Tenant(name="Security RBAC Test", slug=f"security-rbac-{uuid.uuid4().hex[:10]}", plan="enterprise")
        db.add(tenant)
        await db.flush()

        user_id = uuid.uuid4()
        db.add(UserAccount(id=user_id, email=f"{user_id}@example.com", hashed_password="x", is_active=True))
        await db.flush()

        profile = UserProfile(user_id=user_id, tenant_id=tenant.id, first_name="Security RBAC Test User", is_active=True)
        db.add(profile)
        await db.flush()

        if permissions:
            role = TenantRole(tenant_id=tenant.id, name="Security RBAC Test Role", is_system=False, hierarchy_level=100)
            db.add(role)
            await db.flush()
            for module, feature, action in permissions:
                # TenantPermission is a global catalog table, unique on
                # (module, feature, action) -- see uix_permission_def
                # (now also declared on the model's __table_args__, and
                # backfilled by migration e2f4a6b8c0d2 for any database
                # that predates that). Get-or-create rather than blind-
                # insert, with .limit(1) ahead of .scalar_one_or_none():
                # same defensive pattern app/middleware/rbac.py's own
                # check_permission already uses, kept here too as
                # belt-and-suspenders in case duplicates are ever
                # reintroduced despite the constraint.
                perm = (await db.execute(
                    select(TenantPermission).where(
                        TenantPermission.module == module,
                        TenantPermission.feature == feature,
                        TenantPermission.action == action,
                    ).limit(1)
                )).scalar_one_or_none()
                if perm is None:
                    perm = TenantPermission(module=module, feature=feature, action=action)
                    db.add(perm)
                    await db.flush()
                db.add(TenantRolePermission(role_id=role.id, permission_id=perm.id, conditions={}))
                await db.flush()
            db.add(TenantUserRole(tenant_id=tenant.id, user_id=profile.id, role_id=role.id))

        return tenant.id, user_id


async def test_user_without_any_security_permissions_receives_neither_tool():
    tenant_id, user_id = await _make_tenant_and_user([])
    try:
        async with db_session() as db:
            tools = await get_tools_for_user(tenant_id, user_id, db)
        tool_names = {t.name for t in tools}
        assert "get_inactive_users" not in tool_names
        assert "get_org_risk_score" not in tool_names
    finally:
        await _cleanup(tenant_id)


async def test_user_with_only_rbac_roles_read_receives_only_inactive_users_tool():
    tenant_id, user_id = await _make_tenant_and_user([("RBAC", "Roles", "Read")])
    try:
        async with db_session() as db:
            tools = await get_tools_for_user(tenant_id, user_id, db)
        tool_names = {t.name for t in tools}
        assert "get_inactive_users" in tool_names
        # Proves the filter is per-tool, not per-module: this permission
        # does not also unlock the org-risk-score tool.
        assert "get_org_risk_score" not in tool_names
    finally:
        await _cleanup(tenant_id)


async def test_user_with_only_audit_logs_read_receives_only_org_risk_score_tool():
    tenant_id, user_id = await _make_tenant_and_user([("Audit", "Logs", "Read")])
    try:
        async with db_session() as db:
            tools = await get_tools_for_user(tenant_id, user_id, db)
        tool_names = {t.name for t in tools}
        assert "get_org_risk_score" in tool_names
        assert "get_inactive_users" not in tool_names
    finally:
        await _cleanup(tenant_id)


async def test_user_with_both_permissions_receives_both_tools():
    tenant_id, user_id = await _make_tenant_and_user([("RBAC", "Roles", "Read"), ("Audit", "Logs", "Read")])
    try:
        async with db_session() as db:
            tools = await get_tools_for_user(tenant_id, user_id, db)
        tool_names = {t.name for t in tools}
        assert "get_inactive_users" in tool_names
        assert "get_org_risk_score" in tool_names
    finally:
        await _cleanup(tenant_id)
