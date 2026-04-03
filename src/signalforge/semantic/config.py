"""Semantic layer configuration.

Reads from workspace config or environment variables.
Zero config = deterministic-only mode (no LLM calls).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SemanticConfig:
    """Configuration for the semantic intelligence layer.

    Resolution order: explicit params > environment variables > defaults.
    When provider is 'none' or no api_key is set, the system runs in
    deterministic-only mode and all enrichment functions return None.
    """

    provider: str = "none"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 60
    enabled: bool = False

    @classmethod
    def from_env(cls, **overrides) -> SemanticConfig:
        """Build config from environment variables with optional overrides."""
        provider = overrides.get("provider", os.getenv("SF_SEMANTIC_PROVIDER", "none"))
        api_key = overrides.get("api_key", os.getenv("SF_SEMANTIC_API_KEY", ""))
        base_url = overrides.get(
            "base_url",
            os.getenv("SF_SEMANTIC_BASE_URL", "https://api.openai.com/v1"),
        )
        model = overrides.get("model", os.getenv("SF_SEMANTIC_MODEL", "gpt-4o-mini"))
        temperature = float(
            overrides.get("temperature", os.getenv("SF_SEMANTIC_TEMPERATURE", "0.3"))
        )
        max_tokens = int(
            overrides.get("max_tokens", os.getenv("SF_SEMANTIC_MAX_TOKENS", "2000"))
        )
        timeout = int(
            overrides.get("timeout", os.getenv("SF_SEMANTIC_TIMEOUT", "60"))
        )

        enabled = provider != "none" and bool(api_key)

        return cls(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            enabled=enabled,
        )

    @classmethod
    def from_workspace_config(cls, config: dict) -> SemanticConfig:
        """Build from a workspace config dict (e.g., workspace.json semantic key)."""
        semantic = config.get("semantic", {})
        return cls.from_env(**semantic)
