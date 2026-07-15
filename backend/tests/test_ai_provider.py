"""
tests/test_ai_provider.py
==========================
Unit tests for the AI provider abstraction (app/services/ai/*). These
mock the OpenAI/Anthropic SDK clients directly — no live API key or
network call required, so they run in CI/offline exactly like every
other test in this suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.ai.base import AIProviderError, AIProviderNotConfiguredError
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai import factory

_SAMPLE_TOOLS = [
    {
        "name": "search_customer",
        "description": "Search for existing customers by name.",
        "input_schema": {
            "type": "object",
            "properties": {"search": {"type": "string"}},
            "required": ["search"],
        },
    }
]


@pytest.mark.asyncio
async def test_openai_provider_returns_text():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="hello from openai"))]
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.complete([{"role": "user", "content": "hi"}])
    assert result == "hello from openai"


@pytest.mark.asyncio
async def test_openai_provider_empty_response_raises():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=None))]
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    with pytest.raises(AIProviderError):
        await provider.complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_openai_provider_api_error_wrapped():
    from openai import APIConnectionError

    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
    provider._client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=MagicMock())
    )

    with pytest.raises(AIProviderError):
        await provider.complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_anthropic_provider_returns_text():
    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")

    text_block = MagicMock(type="text", text="hello from anthropic")
    mock_response = MagicMock(content=[text_block])
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.complete([{"role": "user", "content": "hi"}], system="be helpful")
    assert result == "hello from anthropic"


@pytest.mark.asyncio
async def test_anthropic_provider_empty_content_raises():
    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")
    mock_response = MagicMock(content=[])
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    with pytest.raises(AIProviderError):
        await provider.complete([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# complete_with_tools -- native tool-calling (Billing orchestrator, see
# app/agent/orchestrator/). No prompted-JSON here; these exercise each
# provider's actual tools= parameter and native tool-call response parsing.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anthropic_complete_with_tools_returns_tool_call():
    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")

    # MagicMock(name=...) sets the mock's own debug repr, not a `.name`
    # attribute -- must be assigned post-construction.
    tool_use_block = MagicMock(type="tool_use", id="toolu_123", input={"search": "Acme"})
    tool_use_block.name = "search_customer"
    mock_response = MagicMock(content=[tool_use_block])
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.complete_with_tools([{"role": "user", "content": "find Acme"}], _SAMPLE_TOOLS)

    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["id"] == "toolu_123"
    assert result.tool_calls[0]["name"] == "search_customer"
    assert result.tool_calls[0]["arguments"] == {"search": "Acme"}

    # tools= passed through to the SDK call untouched (already Anthropic's
    # native shape -- no translation needed for Anthropic specifically).
    call_kwargs = provider._client.messages.create.call_args.kwargs
    assert call_kwargs["tools"] == _SAMPLE_TOOLS


@pytest.mark.asyncio
async def test_anthropic_complete_with_tools_returns_text_when_no_tool_needed():
    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")

    text_block = MagicMock(type="text", text="I can help with that.")
    mock_response = MagicMock(content=[text_block])
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.complete_with_tools([{"role": "user", "content": "hi"}], _SAMPLE_TOOLS)

    assert result.text == "I can help with that."
    assert result.tool_calls == []


@pytest.mark.asyncio
async def test_anthropic_complete_with_tools_empty_response_raises():
    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")
    mock_response = MagicMock(content=[])
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    with pytest.raises(AIProviderError):
        await provider.complete_with_tools([{"role": "user", "content": "hi"}], _SAMPLE_TOOLS)


@pytest.mark.asyncio
async def test_anthropic_complete_with_tools_replays_prior_tool_call_and_result():
    """Verifies message translation for the two non-trivial AIMessage
    shapes: a prior assistant tool-call turn, and a tool_result turn
    answering it -- the exact history an orchestrator loop replays on its
    second iteration."""
    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")

    text_block = MagicMock(type="text", text="Found them.")
    mock_response = MagicMock(content=[text_block])
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    history = [
        {"role": "user", "content": "find Acme"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "toolu_123", "name": "search_customer", "arguments": {"search": "Acme"}}],
        },
        {"role": "tool_result", "tool_call_id": "toolu_123", "content": '{"total": 1}'},
    ]
    await provider.complete_with_tools(history, _SAMPLE_TOOLS)

    sent = provider._client.messages.create.call_args.kwargs["messages"]
    assert sent[1]["role"] == "assistant"
    assert sent[1]["content"] == [
        {"type": "tool_use", "id": "toolu_123", "name": "search_customer", "input": {"search": "Acme"}}
    ]
    assert sent[2]["role"] == "user"  # Anthropic has no "tool" role -- tool results are user turns
    assert sent[2]["content"] == [{"type": "tool_result", "tool_use_id": "toolu_123", "content": '{"total": 1}'}]


@pytest.mark.asyncio
async def test_openai_complete_with_tools_returns_tool_call():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

    tool_call = MagicMock(id="call_123")
    tool_call.function.name = "search_customer"
    tool_call.function.arguments = '{"search": "Acme"}'
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=None, tool_calls=[tool_call]))]
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.complete_with_tools([{"role": "user", "content": "find Acme"}], _SAMPLE_TOOLS)

    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["id"] == "call_123"
    assert result.tool_calls[0]["name"] == "search_customer"
    assert result.tool_calls[0]["arguments"] == {"search": "Acme"}

    # tools= translated into OpenAI's function-call wrapper shape.
    call_kwargs = provider._client.chat.completions.create.call_args.kwargs
    assert call_kwargs["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "search_customer",
                "description": "Search for existing customers by name.",
                "parameters": _SAMPLE_TOOLS[0]["input_schema"],
            },
        }
    ]


@pytest.mark.asyncio
async def test_openai_complete_with_tools_returns_text_when_no_tool_needed():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="I can help with that.", tool_calls=None))]
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.complete_with_tools([{"role": "user", "content": "hi"}], _SAMPLE_TOOLS)

    assert result.text == "I can help with that."
    assert result.tool_calls == []


@pytest.mark.asyncio
async def test_openai_complete_with_tools_empty_response_raises():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=None, tool_calls=None))]
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    with pytest.raises(AIProviderError):
        await provider.complete_with_tools([{"role": "user", "content": "hi"}], _SAMPLE_TOOLS)


@pytest.mark.asyncio
async def test_openai_complete_with_tools_malformed_arguments_raises():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

    tool_call = MagicMock(id="call_123")
    tool_call.function.name = "search_customer"
    tool_call.function.arguments = "{not valid json"
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=None, tool_calls=[tool_call]))]
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    with pytest.raises(AIProviderError):
        await provider.complete_with_tools([{"role": "user", "content": "find Acme"}], _SAMPLE_TOOLS)


@pytest.mark.asyncio
async def test_openai_complete_with_tools_replays_prior_tool_call_and_result():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Found them.", tool_calls=None))]
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    history = [
        {"role": "user", "content": "find Acme"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_123", "name": "search_customer", "arguments": {"search": "Acme"}}],
        },
        {"role": "tool_result", "tool_call_id": "call_123", "content": '{"total": 1}'},
    ]
    await provider.complete_with_tools(history, _SAMPLE_TOOLS)

    sent = provider._client.chat.completions.create.call_args.kwargs["messages"]
    assert sent[1]["role"] == "assistant"
    assert sent[1]["tool_calls"] == [
        {"id": "call_123", "type": "function", "function": {"name": "search_customer", "arguments": '{"search": "Acme"}'}}
    ]
    assert sent[2] == {"role": "tool", "tool_call_id": "call_123", "content": '{"total": 1}'}


def test_factory_raises_when_no_key_configured(monkeypatch):
    factory._reset_cache_for_tests()
    monkeypatch.setattr("app.services.ai.factory.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.services.ai.factory.settings.AI_PROVIDER", "openai")

    with pytest.raises(AIProviderNotConfiguredError):
        factory.get_ai_provider()


def test_factory_unknown_provider_raises(monkeypatch):
    factory._reset_cache_for_tests()
    with pytest.raises(AIProviderNotConfiguredError):
        factory.get_ai_provider("not-a-real-provider")


def test_factory_returns_configured_openai_provider(monkeypatch):
    factory._reset_cache_for_tests()
    monkeypatch.setattr("app.services.ai.factory.settings.OPENAI_API_KEY", "sk-fake")
    monkeypatch.setattr("app.services.ai.factory.settings.AI_PROVIDER", "openai")

    provider = factory.get_ai_provider()
    assert provider.name == "openai"
    # Cached: a second call returns the same instance
    assert factory.get_ai_provider() is provider
    factory._reset_cache_for_tests()


def test_factory_returns_configured_anthropic_provider(monkeypatch):
    factory._reset_cache_for_tests()
    monkeypatch.setattr("app.services.ai.factory.settings.ANTHROPIC_API_KEY", "sk-ant-fake")

    provider = factory.get_ai_provider("anthropic")
    assert provider.name == "anthropic"
    factory._reset_cache_for_tests()
