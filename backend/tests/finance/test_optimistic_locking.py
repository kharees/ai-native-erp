"""
tests/finance/test_optimistic_locking.py
===========================================
Validates optimistic-locking on Account (Chart of Accounts) updates
(Sprint 4 #36): no version column existed on any frequently-edited
document, so two concurrent PATCH /accounts/{id} calls would silently
last-write-win.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_account(async_client: AsyncClient, setup_tenant, auth_headers) -> tuple[str, int]:
    grp_resp = await async_client.post(
        "/api/v1/finance-core/account-groups",
        json={"tenant_id": str(setup_tenant.id), "code": "OL-1000", "name": "Optimistic Lock Test", "category": "asset"},
        headers=auth_headers,
    )
    group_id = grp_resp.json()["id"]
    acc_resp = await async_client.post(
        "/api/v1/finance-core/accounts",
        json={"tenant_id": str(setup_tenant.id), "group_id": group_id, "account_code": "OL-1100", "name": "Lock Test Account"},
        headers=auth_headers,
    )
    assert acc_resp.status_code == 201, acc_resp.json()
    body = acc_resp.json()
    return body["id"], body["version"]


async def test_new_account_starts_at_version_one(async_client: AsyncClient, setup_tenant, auth_headers):
    _, version = await _create_account(async_client, setup_tenant, auth_headers)
    assert version == 1


async def test_update_without_expected_version_still_works(async_client: AsyncClient, setup_tenant, auth_headers):
    """Backward compatible: omitting expected_version skips the check
    entirely, matching pre-#36 behavior for callers that don't send it."""
    account_id, _ = await _create_account(async_client, setup_tenant, auth_headers)

    resp = await async_client.patch(
        f"/api/v1/finance-core/accounts/{account_id}",
        json={"name": "Renamed Without Version Check"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Without Version Check"
    assert resp.json()["version"] == 2


async def test_stale_expected_version_rejected_with_409(async_client: AsyncClient, setup_tenant, auth_headers):
    account_id, version = await _create_account(async_client, setup_tenant, auth_headers)

    # First edit succeeds and bumps the version.
    first = await async_client.patch(
        f"/api/v1/finance-core/accounts/{account_id}",
        json={"name": "First Editor's Change", "expected_version": version},
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert first.json()["version"] == version + 1

    # A second editor working from the now-stale version they originally
    # read gets rejected instead of silently clobbering the first edit.
    second = await async_client.patch(
        f"/api/v1/finance-core/accounts/{account_id}",
        json={"name": "Second Editor's Conflicting Change", "expected_version": version},
        headers=auth_headers,
    )
    assert second.status_code == 409

    # The first editor's change is intact — not overwritten.
    get_resp = await async_client.get(f"/api/v1/finance-core/accounts/{account_id}", headers=auth_headers)
    assert get_resp.json()["name"] == "First Editor's Change"
