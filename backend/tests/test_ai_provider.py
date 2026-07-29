"""
tests/test_ai_provider.py
==========================
Unit tests for the AI provider abstraction (app/services/ai/*). These
mock the OpenAI/Anthropic SDK clients and Gemini's httpx client directly
— no live API key or network call required, so they run in CI/offline
exactly like every other test in this suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.ai.base import AIProviderError, AIProviderNotConfiguredError
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.gemini_provider import GeminiProvider, _sanitize_schema_for_gemini
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


# ---------------------------------------------------------------------------
# Gemini -- no vendor SDK (see gemini_provider.py's module docstring for
# why), so these mock provider._client.post (httpx.AsyncClient) directly
# instead of a vendor SDK method, returning a MagicMock shaped like an
# httpx.Response (status_code + .json()).
# ---------------------------------------------------------------------------

def test_sanitize_schema_for_gemini_converts_exclusive_bounds_recursively():
    """Discovered live: Gemini's function-calling schema validator rejects
    exclusiveMinimum/exclusiveMaximum with a 400, unlike Anthropic/OpenAI
    which just pass the schema through as model-facing documentation."""
    schema = {
        "type": "object",
        "properties": {
            "amount": {"type": "number", "exclusiveMinimum": 0},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "quantity": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 100},
                    },
                },
            },
        },
    }

    sanitized = _sanitize_schema_for_gemini(schema)

    assert sanitized["properties"]["amount"] == {"type": "number", "minimum": 0}
    assert sanitized["properties"]["items"]["items"]["properties"]["quantity"] == {
        "type": "number", "minimum": 0, "maximum": 100,
    }
    # Untouched keywords pass through as-is.
    assert sanitized["type"] == "object"


def _gemini_response(json_body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(status_code=status_code)
    resp.json.return_value = json_body
    resp.text = str(json_body)
    return resp


@pytest.mark.asyncio
async def test_gemini_provider_returns_text():
    provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
    provider._client.post = AsyncMock(return_value=_gemini_response({
        "candidates": [{"content": {"parts": [{"text": "hello from gemini"}]}}]
    }))

    result = await provider.complete([{"role": "user", "content": "hi"}])
    assert result == "hello from gemini"


@pytest.mark.asyncio
async def test_gemini_provider_empty_candidates_raises():
    provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
    provider._client.post = AsyncMock(return_value=_gemini_response({"candidates": []}))

    with pytest.raises(AIProviderError):
        await provider.complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_gemini_provider_auth_error_wrapped():
    provider = GeminiProvider(api_key="bad-key", model="gemini-2.0-flash")
    provider._client.post = AsyncMock(return_value=_gemini_response({"error": {"message": "API key not valid"}}, status_code=400))

    with pytest.raises(AIProviderError):
        await provider.complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_gemini_complete_with_tools_returns_tool_call():
    provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
    provider._client.post = AsyncMock(return_value=_gemini_response({
        "candidates": [{"content": {"parts": [
            {"functionCall": {"name": "search_customer", "args": {"search": "Acme"}}}
        ]}}]
    }))

    result = await provider.complete_with_tools([{"role": "user", "content": "find Acme"}], _SAMPLE_TOOLS)

    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "search_customer"
    assert result.tool_calls[0]["arguments"] == {"search": "Acme"}

    # tools= translated into Gemini's functionDeclarations wrapper shape.
    call_kwargs = provider._client.post.call_args.kwargs
    assert call_kwargs["json"]["tools"] == [{
        "functionDeclarations": [{
            "name": "search_customer",
            "description": "Search for existing customers by name.",
            "parameters": _SAMPLE_TOOLS[0]["input_schema"],
        }]
    }]


@pytest.mark.asyncio
async def test_gemini_complete_with_tools_returns_text_when_no_tool_needed():
    provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
    provider._client.post = AsyncMock(return_value=_gemini_response({
        "candidates": [{"content": {"parts": [{"text": "I can help with that."}]}}]
    }))

    result = await provider.complete_with_tools([{"role": "user", "content": "hi"}], _SAMPLE_TOOLS)

    assert result.text == "I can help with that."
    assert result.tool_calls == []


@pytest.mark.asyncio
async def test_gemini_complete_with_tools_empty_response_raises():
    provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
    provider._client.post = AsyncMock(return_value=_gemini_response({
        "candidates": [{"content": {"parts": []}}]
    }))

    with pytest.raises(AIProviderError):
        await provider.complete_with_tools([{"role": "user", "content": "hi"}], _SAMPLE_TOOLS)


@pytest.mark.asyncio
async def test_gemini_complete_with_tools_replays_prior_tool_call_and_result():
    """Verifies message translation for the two non-trivial AIMessage
    shapes, including Gemini's id->name resolution for tool_result turns
    (Gemini's functionResponse matches by name, not the call id this
    codebase's tool_result AIMessage actually carries)."""
    provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
    provider._client.post = AsyncMock(return_value=_gemini_response({
        "candidates": [{"content": {"parts": [{"text": "Found them."}]}}]
    }))

    history = [
        {"role": "user", "content": "find Acme"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_0", "name": "search_customer", "arguments": {"search": "Acme"}}],
        },
        {"role": "tool_result", "tool_call_id": "call_0", "content": '{"total": 1}'},
    ]
    await provider.complete_with_tools(history, _SAMPLE_TOOLS)

    sent = provider._client.post.call_args.kwargs["json"]["contents"]
    assert sent[1]["role"] == "model"
    assert sent[1]["parts"] == [{"functionCall": {"name": "search_customer", "args": {"search": "Acme"}}}]
    assert sent[2]["role"] == "user"  # Gemini has no "tool" role -- results are user turns
    assert sent[2]["parts"] == [
        {"functionResponse": {"name": "search_customer", "response": {"content": '{"total": 1}'}}}
    ]


# ---------------------------------------------------------------------------
# Image support -- app/services/ai/base.py's AIImageBlock, translated to
# each provider's own native image shape. complete() now routes through
# each provider's _to_*_messages/_to_*_contents translator (previously
# Anthropic/OpenAI's complete() bypassed it entirely, passing raw messages
# straight to the SDK -- fixed here so image support, and the translator's
# existing tool_calls/tool_result handling, both work through complete()
# consistently with complete_with_tools()).
# ---------------------------------------------------------------------------

_SAMPLE_IMAGE_MESSAGE = [{
    "role": "user",
    "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image", "media_type": "image/jpeg", "data": "ZmFrZWJhc2U2NGRhdGE="},
    ],
}]


@pytest.mark.asyncio
async def test_anthropic_complete_sends_native_image_content_block():
    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")
    text_block = MagicMock(type="text", text="A cat.")
    provider._client.messages.create = AsyncMock(return_value=MagicMock(content=[text_block]))

    await provider.complete(_SAMPLE_IMAGE_MESSAGE)

    sent = provider._client.messages.create.call_args.kwargs["messages"]
    assert sent == [{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "ZmFrZWJhc2U2NGRhdGE="}},
        ],
    }]


@pytest.mark.asyncio
async def test_anthropic_complete_with_tools_sends_native_image_content_block():
    provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")
    text_block = MagicMock(type="text", text="A cat.")
    provider._client.messages.create = AsyncMock(return_value=MagicMock(content=[text_block]))

    await provider.complete_with_tools(_SAMPLE_IMAGE_MESSAGE, _SAMPLE_TOOLS)

    sent = provider._client.messages.create.call_args.kwargs["messages"]
    assert sent[0]["content"][1] == {
        "type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "ZmFrZWJhc2U2NGRhdGE="},
    }


@pytest.mark.asyncio
async def test_anthropic_raises_on_image_with_non_vision_model():
    provider = AnthropicProvider(api_key="test-key", model="claude-2.1")
    provider._client.messages.create = AsyncMock()

    with pytest.raises(AIProviderError, match="does not support image input"):
        await provider.complete(_SAMPLE_IMAGE_MESSAGE)

    # No silent drop/fallback -- the SDK is never even called.
    provider._client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_openai_complete_sends_image_url_data_uri():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="A cat."))]
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    await provider.complete(_SAMPLE_IMAGE_MESSAGE)

    sent = provider._client.chat.completions.create.call_args.kwargs["messages"]
    assert sent == [{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,ZmFrZWJhc2U2NGRhdGE="}},
        ],
    }]


@pytest.mark.asyncio
async def test_openai_raises_on_image_with_non_vision_model():
    provider = OpenAIProvider(api_key="test-key", model="gpt-3.5-turbo")
    provider._client.chat.completions.create = AsyncMock()

    with pytest.raises(AIProviderError, match="does not support image input"):
        await provider.complete(_SAMPLE_IMAGE_MESSAGE)

    provider._client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_gemini_complete_sends_inline_data_image_part():
    provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
    provider._client.post = AsyncMock(return_value=_gemini_response({
        "candidates": [{"content": {"parts": [{"text": "A cat."}]}}]
    }))

    await provider.complete(_SAMPLE_IMAGE_MESSAGE)

    sent = provider._client.post.call_args.kwargs["json"]["contents"]
    assert sent == [{
        "role": "user",
        "parts": [
            {"text": "What's in this image?"},
            {"inline_data": {"mime_type": "image/jpeg", "data": "ZmFrZWJhc2U2NGRhdGE="}},
        ],
    }]


@pytest.mark.asyncio
async def test_gemini_raises_on_image_with_non_vision_model():
    provider = GeminiProvider(api_key="test-key", model="text-bison-001")
    provider._client.post = AsyncMock()

    with pytest.raises(AIProviderError, match="does not support image input"):
        await provider.complete(_SAMPLE_IMAGE_MESSAGE)

    provider._client.post.assert_not_called()


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


def test_factory_model_override_returns_distinct_cached_instance(monkeypatch):
    factory._reset_cache_for_tests()
    monkeypatch.setattr("app.services.ai.factory.settings.OPENAI_API_KEY", "sk-fake")
    monkeypatch.setattr("app.services.ai.factory.settings.AI_PROVIDER", "openai")
    monkeypatch.setattr("app.services.ai.factory.settings.AI_MODEL_OPENAI", "gpt-4o-mini")
    monkeypatch.setattr("app.services.ai.factory.settings.AI_MODEL_VISION", "gpt-4o")

    default_provider = factory.get_ai_provider()
    vision_provider = factory.get_ai_provider(model=factory.settings.AI_MODEL_VISION)

    assert default_provider is not vision_provider
    assert default_provider._model == "gpt-4o-mini"
    assert vision_provider._model == "gpt-4o"
    # Each is independently cached by (name, model) -- calling again with
    # the same override returns the same instance, not a fresh one.
    assert factory.get_ai_provider(model="gpt-4o") is vision_provider
    factory._reset_cache_for_tests()


def test_factory_returns_configured_anthropic_provider(monkeypatch):
    factory._reset_cache_for_tests()
    monkeypatch.setattr("app.services.ai.factory.settings.ANTHROPIC_API_KEY", "sk-ant-fake")

    provider = factory.get_ai_provider("anthropic")
    assert provider.name == "anthropic"
    factory._reset_cache_for_tests()


def test_factory_returns_configured_gemini_provider(monkeypatch):
    factory._reset_cache_for_tests()
    monkeypatch.setattr("app.services.ai.factory.settings.GEMINI_API_KEY", "gm-fake")

    provider = factory.get_ai_provider("gemini")
    assert provider.name == "gemini"
    factory._reset_cache_for_tests()
