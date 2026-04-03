"""LLM Provider abstraction.

Uses the OpenAI SDK as the universal protocol since nearly every provider
now supports the OpenAI-compatible API format:
- OpenAI, Anthropic (via proxy), Zhipu AI, Together, Groq, Mistral
- Ollama, llama.cpp server, vLLM, LM Studio (local models)
- Any OpenAI-compatible endpoint

This avoids heavy dependencies like litellm while maintaining universality.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol, runtime_checkable

from .config import SemanticConfig

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMProvider(Protocol):
    """Interface for LLM providers."""

    def complete(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        """Send a completion request. Returns None if unavailable or on error."""
        ...

    def available(self) -> bool:
        """Check if the provider is configured and ready."""
        ...


class OpenAIProvider:
    """OpenAI-compatible provider. Works with any endpoint that speaks the
    OpenAI chat completions format.

    Supports:
    - api.openai.com (OpenAI)
    - open.bigmodel.cn/api/paas/v4 (Zhipu AI / GLM models)
    - api.together.xyz (Together AI)
    - api.groq.com/openai/v1 (Groq)
    - localhost:11434/v1 (Ollama)
    - localhost:8080/v1 (llama.cpp server)
    - And many more...
    """

    def __init__(self, config: SemanticConfig) -> None:
        self.config = config
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-init the OpenAI client to avoid import overhead when unused."""
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
            return self._client
        except ImportError:
            logger.warning(
                "openai package not installed. Install with: pip install openai"
            )
            return None

    def available(self) -> bool:
        return self.config.enabled

    def complete(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        if not self.available():
            return None

        client = self._get_client()
        if client is None:
            return None

        try:
            kwargs: dict[str, Any] = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature or self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            if content:
                return content.strip()
            return None

        except Exception as exc:
            logger.warning("LLM completion failed: %s", exc)
            return None

    def complete_structured(
        self,
        system: str,
        user: str,
        expected_keys: list[str] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict | None:
        """Complete with JSON mode and return parsed dict.

        Validates that the response is valid JSON and optionally checks
        for expected keys. Returns None on any failure.
        """
        raw = self.complete(
            system=system,
            user=user,
            json_mode=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if raw is None:
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON")
            return None

        if expected_keys and isinstance(parsed, dict):
            missing = [k for k in expected_keys if k not in parsed]
            if missing:
                logger.warning("LLM JSON missing keys: %s", missing)

        return parsed


class NoOpProvider:
    """Provider that always returns None. Used when no LLM is configured.

    This ensures the semantic layer gracefully degrades to
    deterministic-only mode without any code changes.
    """

    def complete(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        return None

    def available(self) -> bool:
        return False

    def complete_structured(
        self,
        system: str,
        user: str,
        expected_keys: list[str] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict | None:
        return None


def create_provider(config: SemanticConfig | None = None) -> LLMProvider:
    """Factory: create the appropriate provider from config.

    Returns NoOpProvider if config is None or provider is disabled.
    """
    if config is None or not config.enabled:
        return NoOpProvider()

    return OpenAIProvider(config)
