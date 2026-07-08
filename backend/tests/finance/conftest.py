from datetime import datetime, timezone, timedelta
import pytest_asyncio
import unittest.mock

@pytest_asyncio.fixture(scope="session", autouse=True)
def patch_rbac():
    """Bypass RequirePermission for all finance tests to avoid needing full DB role setup"""
    with unittest.mock.patch("app.middleware.rbac.RequirePermission.__call__", return_value=True):
        yield
