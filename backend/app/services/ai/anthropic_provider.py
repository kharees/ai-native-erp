"""
app/services/ai/anthropic_provider.py
========================================
Anthropic implementation of the AIProvider interface.
"""

from __future__ import annotations

import structlog
from anthropic import AsyncAnthropic, APIError, APIConnectionError, AuthenticationError

from app.services.ai.base import AIMessage, AIProvider, AIProviderError

log = structlog.get_logger(__name__)


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        try:
            response = await self._client.messages.create(
                model=self._model,
                system=system or "",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except AuthenticationError as exc:
            log.error("anthropic_auth_failed", error=str(exc))
            raise AIProviderError("Anthropic authentication failed — check ANTHROPIC_API_KEY.") from exc
        except APIConnectionError as exc:
            log.error("anthropic_connection_failed", error=str(exc))
            raise AIProviderError("Could not reach Anthropic.") from exc
        except APIError as exc:
            log.error("anthropic_api_error", error=str(exc))
            raise AIProviderError(f"Anthropic API error: {exc}") from exc

        if not response.content:
            raise AIProviderError("Anthropic returned an empty response.")

        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        if not text_blocks:
            raise AIProviderError("Anthropic response contained no text content.")
        return "".join(text_blocks)
