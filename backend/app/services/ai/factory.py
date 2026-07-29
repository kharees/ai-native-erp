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

    # For a call sending an image, override the model explicitly rather
    # than trusting the provider's default text model is vision-capable:
    vision_provider = get_ai_provider(model=settings.AI_MODEL_VISION)
"""

from __future__ import annotations

from app.core.config import settings
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import AIProvider, AIProviderNotConfiguredError
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider

_PROVIDER_CACHE: dict[tuple[str, str], AIProvider] = {}


def get_ai_provider(provider_name: str | None = None, model: str | None = None) -> AIProvider:
    """
    Return the AIProvider named by `provider_name`, or `settings.AI_PROVIDER`
    if not given. Raises AIProviderNotConfiguredError if that provider's API
    key is empty — callers must not treat a missing key as "fall back to
    fabricated data."

    `model` overrides that provider's configured default model
    (settings.AI_MODEL_OPENAI/ANTHROPIC/GEMINI) for this call only -- e.g.
    settings.AI_MODEL_VISION for a call that sends an image. The provider
    cache is keyed on (name, model), not just name, so a default-model
    instance and a model-override instance for the same provider are
    cached separately rather than one clobbering or shadowing the other.
    """
    name = (provider_name or settings.AI_PROVIDER).lower()

    if name == "openai":
        default_model = settings.AI_MODEL_OPENAI
    elif name == "anthropic":
        default_model = settings.AI_MODEL_ANTHROPIC
    elif name == "gemini":
        default_model = settings.AI_MODEL_GEMINI
    else:
        raise AIProviderNotConfiguredError(
            f"Unknown AI_PROVIDER '{name}' — expected 'openai', 'anthropic', or 'gemini'."
        )
    effective_model = model or default_model

    cache_key = (name, effective_model)
    if cache_key in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[cache_key]

    if name == "openai":
        if not settings.OPENAI_API_KEY:
            raise AIProviderNotConfiguredError(
                "AI_PROVIDER is 'openai' but OPENAI_API_KEY is not set."
            )
        provider: AIProvider = OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=effective_model)
    elif name == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise AIProviderNotConfiguredError(
                "AI_PROVIDER is 'anthropic' but ANTHROPIC_API_KEY is not set."
            )
        provider = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, model=effective_model)
    else:
        if not settings.GEMINI_API_KEY:
            raise AIProviderNotConfiguredError(
                "AI_PROVIDER is 'gemini' but GEMINI_API_KEY is not set."
            )
        provider = GeminiProvider(api_key=settings.GEMINI_API_KEY, model=effective_model)

    _PROVIDER_CACHE[cache_key] = provider
    return provider


def _reset_cache_for_tests() -> None:
    """Test-only: clear the provider cache so tests can reconfigure settings."""
    _PROVIDER_CACHE.clear()
