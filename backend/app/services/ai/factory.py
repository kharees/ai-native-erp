"""
app/services/ai/factory.py
============================
Selects and constructs the configured AIProvider.

Usage
-----
    from app.services.ai import get_ai_provider, AIProviderNotConfiguredError

    try:
        provider = get_ai_provider()
        text = await provider.complete([{"role": "user", "content": "..."}])
    except AIProviderNotConfiguredError:
        # No API key set for the configured provider — surface this
        # honestly rather than fabricating a response.
        ...
"""

from __future__ import annotations

from app.core.config import settings
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import AIProvider, AIProviderNotConfiguredError
from app.services.ai.openai_provider import OpenAIProvider

_PROVIDER_CACHE: dict[str, AIProvider] = {}


def get_ai_provider(provider_name: str | None = None) -> AIProvider:
    """
    Return the AIProvider named by `provider_name`, or `settings.AI_PROVIDER`
    if not given. Raises AIProviderNotConfiguredError if that provider's API
    key is empty — callers must not treat a missing key as "fall back to
    fabricated data."
    """
    name = (provider_name or settings.AI_PROVIDER).lower()

    if name in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[name]

    if name == "openai":
        if not settings.OPENAI_API_KEY:
            raise AIProviderNotConfiguredError(
                "AI_PROVIDER is 'openai' but OPENAI_API_KEY is not set."
            )
        provider: AIProvider = OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.AI_MODEL_OPENAI)
    elif name == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise AIProviderNotConfiguredError(
                "AI_PROVIDER is 'anthropic' but ANTHROPIC_API_KEY is not set."
            )
        provider = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.AI_MODEL_ANTHROPIC)
    else:
        raise AIProviderNotConfiguredError(
            f"Unknown AI_PROVIDER '{name}' — expected 'openai' or 'anthropic'."
        )

    _PROVIDER_CACHE[name] = provider
    return provider


def _reset_cache_for_tests() -> None:
    """Test-only: clear the provider cache so tests can reconfigure settings."""
    _PROVIDER_CACHE.clear()
