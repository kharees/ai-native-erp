"""
tests/test_analytics_tool_schemas.py
=======================================
Schema/handler consistency for app/agent/tools/analytics_tools.py, using
the shared assert_tool_schema_matches_handler helper (tests/
agent_tool_schema_checks.py) -- the same reusable pattern
tests/test_billing_tool_schemas.py and tests/test_inventory_tool_schemas.py
already established, applied to the third tool module.
"""
import pytest

from app.agent.tools.analytics_tools import ANALYTICS_TOOLS
from tests.agent_tool_schema_checks import assert_tool_schema_matches_handler

# Analytics tools are read-only -- only tenant_id is ever injected, no
# user_id/idempotency_key (nothing here mutates or needs to be retried
# safely).
_INJECTED_PARAMS = {"tenant_id"}


def _tool_def(name: str):
    return next(t for t in ANALYTICS_TOOLS if t.name == name)


@pytest.mark.parametrize("tool_name", [
    "get_sales_summary", "get_top_items", "get_low_stock_items",
    "get_outstanding_dues", "get_customer_summary",
])
def test_tool_schema_fields_match_real_handler_parameters(tool_name):
    assert_tool_schema_matches_handler(_tool_def(tool_name), injected_params=_INJECTED_PARAMS)


@pytest.mark.parametrize("tool", ANALYTICS_TOOLS)
def test_no_analytics_tool_requires_confirmation(tool):
    assert tool.requires_confirmation is False
