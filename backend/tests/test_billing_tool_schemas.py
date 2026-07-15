"""
tests/test_billing_tool_schemas.py
=====================================
Runs the REAL app/agent/tools/billing_tools.py tool definitions (not a
synthetic sample schema) through complete_with_tools() for both
providers, with realistically-shaped mocked SDK responses. Purpose:
catch a schema-specific translation bug -- e.g. create_invoice's nested
`items` array getting mangled, or a field name in a tool's input_schema
silently drifting out of sync with its handler's real parameter names --
before it's tangled up with orchestrator logic on top.

tests/test_ai_provider.py already covers the *generic* AIToolCall
plumbing (arbitrary tool, arbitrary arguments) in isolation. This file
is specifically about the real 3 tools' real schemas.

The schema/handler consistency check below uses the shared
assert_tool_schema_matches_handler helper (tests/agent_tool_schema_checks.py)
rather than its own inline logic -- this is the reference usage
Inventory/Finance's future tool-schema test files should copy.
"""
import inspect
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.tools.billing_tools import BILLING_TOOLS
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.openai_provider import OpenAIProvider
from tests.agent_tool_schema_checks import assert_tool_schema_matches_handler

_INJECTED_PARAMS = {"tenant_id", "user_id", "idempotency_key"}

# Realistic sample arguments a model would actually produce for each real
# tool, matching each tool's real input_schema -- not a placeholder.
_SAMPLE_ARGUMENTS = {
    "create_invoice": {
        "customer_id": str(uuid.uuid4()),
        "invoice_number": "INV-2026-001",
        "currency": "INR",
        "is_tax_inclusive": False,
        "items": [
            {
                "item_id": str(uuid.uuid4()),
                "quantity": 2,
                "unit_price": 50.0,
                "line_total": 100.0,
                "hsn_sac_code": "998311",
            }
        ],
        "subtotal": 100.0,
        "total_amount": 100.0,
    },
    "record_payment": {
        "customer_id": str(uuid.uuid4()),
        "receipt_number": "REC-2026-001",
        "payment_mode": "BANK",
        "amount_received": 250.0,
        "unallocated_amount": 250.0,
        "bank_account_id": str(uuid.uuid4()),
        "reference_number": "REF-001",
    },
    "search_customer": {
        "search": "Acme",
        "limit": 20,
    },
}


def _tool_def(name: str):
    return next(t for t in BILLING_TOOLS if t.name == name)


# ---------------------------------------------------------------------------
# Schema/handler consistency -- provider-independent, pure introspection.
# Catches a field renamed in the schema but not the handler (or vice
# versa) mechanically, without needing a provider round-trip at all.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool_name", ["create_invoice", "record_payment", "search_customer"])
def test_tool_schema_fields_match_real_handler_parameters(tool_name):
    assert_tool_schema_matches_handler(_tool_def(tool_name), injected_params=_INJECTED_PARAMS)


# ---------------------------------------------------------------------------
# Real provider round-trip: real tool schema out, realistic tool-call
# arguments back in, both checked against the actual dict shape.
# ---------------------------------------------------------------------------

def _mock_anthropic_tool_call_response(call_id: str, name: str, arguments: dict):
    block = MagicMock(type="tool_use", id=call_id, input=arguments)
    block.name = name  # MagicMock(name=...) is reserved for the mock's own repr, not an attribute
    return MagicMock(content=[block])


def _mock_openai_tool_call_response(call_id: str, name: str, arguments: dict):
    call = MagicMock(id=call_id)
    call.function.name = name
    call.function.arguments = json.dumps(arguments)
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=None, tool_calls=[call]))]
    return response


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["create_invoice", "record_payment", "search_customer"])
async def test_real_tool_schema_round_trips_through_anthropic(tool_name):
    tool = _tool_def(tool_name)
    provider_schema = tool.to_provider_schema()
    sample_args = _SAMPLE_ARGUMENTS[tool_name]

    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")
    provider._client.messages.create = AsyncMock(
        return_value=_mock_anthropic_tool_call_response("toolu_1", tool_name, sample_args)
    )

    result = await provider.complete_with_tools(
        [{"role": "user", "content": "please do the thing"}], [provider_schema]
    )

    # The real input_schema -- including create_invoice's nested items
    # array -- reached the SDK call untouched, not reshaped or truncated.
    sent_tools = provider._client.messages.create.call_args.kwargs["tools"]
    assert sent_tools == [provider_schema]
    assert sent_tools[0]["input_schema"] == tool.input_schema

    assert result.tool_calls[0]["name"] == tool_name
    assert result.tool_calls[0]["arguments"] == sample_args

    # The parsed arguments are exactly what the real handler would receive
    # as **kwargs -- every key is a real parameter, nothing was dropped or
    # renamed in transit.
    handler_params = set(inspect.signature(tool.handler).parameters.keys())
    assert set(result.tool_calls[0]["arguments"].keys()) <= handler_params


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["create_invoice", "record_payment", "search_customer"])
async def test_real_tool_schema_round_trips_through_openai(tool_name):
    tool = _tool_def(tool_name)
    provider_schema = tool.to_provider_schema()
    sample_args = _SAMPLE_ARGUMENTS[tool_name]

    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
    provider._client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_tool_call_response("call_1", tool_name, sample_args)
    )

    result = await provider.complete_with_tools(
        [{"role": "user", "content": "please do the thing"}], [provider_schema]
    )

    # The real input_schema round-trips through OpenAI's function-call
    # wrapper (nested under "parameters") with no loss, including
    # create_invoice's nested items array.
    sent_tools = provider._client.chat.completions.create.call_args.kwargs["tools"]
    assert sent_tools == [
        {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema}}
    ]

    assert result.tool_calls[0]["name"] == tool_name
    # Round-tripped through json.dumps/json.loads at the OpenAI wire
    # boundary -- this is specifically where nested structures (items:
    # list[dict]) are most likely to silently lose fidelity if the
    # translation were hand-rolled instead of using the stdlib json module.
    assert result.tool_calls[0]["arguments"] == sample_args

    handler_params = set(inspect.signature(tool.handler).parameters.keys())
    assert set(result.tool_calls[0]["arguments"].keys()) <= handler_params
