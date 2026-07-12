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
