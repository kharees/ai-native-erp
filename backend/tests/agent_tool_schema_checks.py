"""
tests/agent_tool_schema_checks.py
====================================
Shared structural check for AI OS tool definitions (app/agent/tools/*):
verifies a tool's input_schema stays consistent with its handler's real
parameter list, and that no orchestrator-injected parameter (tenant_id,
user_id, idempotency_key, or whatever else a given module's handlers
inject) ever leaks into the schema a model sees.

Not a test file itself (no test_ functions, not collected by pytest) --
import assert_tool_schema_matches_handler from each module's own test
file (see tests/test_billing_tool_schemas.py for the reference usage)
and parametrize it over that module's own ToolDefinition list. This
exists so the guarantee is standard for every module's tools by
construction, not something re-derived by hand each time a new module's
tool registry gets built (Inventory, Finance, ...).
"""

import inspect
from typing import Iterable

from app.agent.tools.base import ToolDefinition


def assert_tool_schema_matches_handler(tool: ToolDefinition, injected_params: Iterable[str]) -> None:
    """
    injected_params: every parameter this tool's handler requires that is
    supplied by the orchestrator rather than the model (e.g.
    {"tenant_id", "user_id"} for a read-only tool, or
    {"tenant_id", "user_id", "idempotency_key"} for a money-mutating one).
    Not defaulted to a fixed set here deliberately -- different modules'
    handlers inject different things, and hardcoding Billing's set would
    silently mis-check a module that doesn't use idempotency_key at all.
    """
    injected = set(injected_params)
    handler_params = inspect.signature(tool.handler).parameters

    schema_properties = set(tool.input_schema.get("properties", {}).keys())
    schema_required = set(tool.input_schema.get("required", []))
    handler_param_names = set(handler_params.keys())

    # Every property the schema exposes to the model must be a real
    # handler parameter name, or a call built from model-supplied
    # arguments raises TypeError at dispatch time instead of failing here.
    assert schema_properties <= handler_param_names, (
        f"{tool.name}: schema properties not present on the handler: "
        f"{schema_properties - handler_param_names}"
    )

    # Every handler parameter with no default (required) must either be
    # schema-required, or be one of the orchestrator-injected params that
    # are deliberately never in the schema.
    handler_required = {
        name for name, p in handler_params.items()
        if p.default is inspect.Parameter.empty
    }
    assert handler_required - injected == schema_required, (
        f"{tool.name}: handler-required params {handler_required - injected} "
        f"don't match schema-required {schema_required}"
    )

    # The hard rule itself, checked mechanically rather than just by
    # convention: none of the injected params ever appear in the schema.
    assert schema_properties.isdisjoint(injected), (
        f"{tool.name}: schema exposes an orchestrator-injected param: "
        f"{schema_properties & injected}"
    )
