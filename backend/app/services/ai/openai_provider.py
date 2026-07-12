"""
app/services/ai/openai_provider.py
====================================
OpenAI implementation of the AIProvider interface.
"""

from __future__ import annotations

import structlog
from openai import AsyncOpenAI, APIError, APIConnectionError, AuthenticationError

from app.services.ai.base import AIMessage, AIProvider, AIProviderError

log = structlog.get_logger(__name__)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend(messages)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except AuthenticationError as exc:
            log.error("openai_auth_failed", error=str(exc))
            raise AIProviderError("OpenAI authentication failed — check OPENAI_API_KEY.") from exc
        except APIConnectionError as exc:
            log.error("openai_connection_failed", error=str(exc))
            raise AIProviderError("Could not reach OpenAI.") from exc
        except APIError as exc:
            log.error("openai_api_error", error=str(exc))
            raise AIProviderError(f"OpenAI API error: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            raise AIProviderError("OpenAI returned an empty response.")
        return content
