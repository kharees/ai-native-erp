"""
tests/test_inventory_tool_schemas.py
=======================================
Schema/handler consistency for app/agent/tools/inventory_tools.py, using
the shared assert_tool_schema_matches_handler helper (tests/
agent_tool_schema_checks.py) -- the same reusable pattern
tests/test_billing_tool_schemas.py established, applied to the second
tool module. Catches a field renamed in a schema but not its handler (or
vice versa) mechanically, without needing a provider round-trip.
"""
import pytest

from app.agent.tools.inventory_tools import INVENTORY_TOOLS
from tests.agent_tool_schema_checks import assert_tool_schema_matches_handler

_INJECTED_PARAMS = {"tenant_id", "user_id", "idempotency_key"}


def _tool_def(name: str):
    return next(t for t in INVENTORY_TOOLS if t.name == name)


@pytest.mark.parametrize("tool_name", ["get_stock_balance", "execute_stock_movement", "search_item"])
def test_tool_schema_fields_match_real_handler_parameters(tool_name):
    assert_tool_schema_matches_handler(_tool_def(tool_name), injected_params=_INJECTED_PARAMS)
