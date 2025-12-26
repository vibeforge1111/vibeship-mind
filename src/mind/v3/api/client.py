"""
Claude API client foundation for Mind v3.

Provides a configurable client for calling Claude models (Haiku, Sonnet, Opus)
with intelligence level controls and graceful fallbacks.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

# Optional anthropic import - handled gracefully if not installed
try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore


@dataclass
class ClaudeConfig:
    """
    Configuration for Claude API client.

    Attributes:
        api_key: Anthropic API key. If None, client is disabled.
        intelligence_level: Controls which features use API calls.
            FREE: No API calls (default)
            LITE: Basic extraction only
            BALANCED: Extraction + reranking
            PRO: All features including summaries
            ULTRA: Maximum quality, more API calls
        max_retries: Maximum retry attempts for failed calls.
        timeout: Request timeout in seconds.
    """

    api_key: str | None = None
    intelligence_level: str = "FREE"
    max_retries: int = 3
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "ClaudeConfig":
        """
        Create config from environment variables.

        Reads:
            ANTHROPIC_API_KEY: API key for Anthropic
            MIND_INTELLIGENCE_LEVEL: Intelligence level (FREE, LITE, BALANCED, PRO, ULTRA)

        Returns:
            ClaudeConfig instance with values from environment.
        """
        return cls(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            intelligence_level=os.environ.get("MIND_INTELLIGENCE_LEVEL", "FREE"),
        )


class ClaudeClient:
    """
    Client for calling Claude models.

    Supports three model tiers: Haiku (fast), Sonnet (balanced), Opus (best).
    Automatically disabled when no API key or FREE intelligence level.
    """

    MODELS: dict[str, str] = {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
    }

    def __init__(self, config: ClaudeConfig) -> None:
        """
        Initialize Claude client.

        Args:
            config: ClaudeConfig instance with API settings.
        """
        self.config = config
        self._anthropic_client: Any | None = None

    @property
    def enabled(self) -> bool:
        """
        Check if client is enabled.

        Client is enabled only when:
        1. API key is set (not None)
        2. Intelligence level is not FREE

        Returns:
            True if client can make API calls, False otherwise.
        """
        return self.config.api_key is not None and self.config.intelligence_level != "FREE"

    def _get_client(self) -> Any | None:
        """
        Get or create the anthropic client.

        Uses lazy initialization - client created on first use.
        Handles missing anthropic package gracefully.

        Returns:
            anthropic.Anthropic instance or None if unavailable.
        """
        if self._anthropic_client is not None:
            return self._anthropic_client

        if anthropic is None:
            return None

        try:
            self._anthropic_client = anthropic.Anthropic(api_key=self.config.api_key)
            return self._anthropic_client
        except Exception:
            return None

    async def _call_model(self, model_key: str, prompt: str, system: str = "") -> str:
        """
        Internal method to call a specific model.

        Args:
            model_key: Key in MODELS dict (haiku, sonnet, opus).
            prompt: User prompt to send.
            system: Optional system prompt.

        Returns:
            Model response text or empty string on error/disabled.
        """
        if not self.enabled:
            return ""

        client = self._get_client()
        if client is None:
            return ""

        try:
            model_id = self.MODELS[model_key]

            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Build request kwargs
            kwargs: dict[str, Any] = {
                "model": model_id,
                "max_tokens": 1024,
                "messages": messages,
            }

            if system:
                kwargs["system"] = system

            response = client.messages.create(**kwargs)

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text

            return ""

        except Exception:
            return ""

    async def call_haiku(self, prompt: str, system: str = "") -> str:
        """
        Call Claude Haiku model.

        Fast, cost-effective model for simple tasks.

        Args:
            prompt: User prompt.
            system: Optional system prompt.

        Returns:
            Model response or empty string if disabled/error.
        """
        return await self._call_model("haiku", prompt, system)

    async def call_sonnet(self, prompt: str, system: str = "") -> str:
        """
        Call Claude Sonnet model.

        Balanced model for most tasks.

        Args:
            prompt: User prompt.
            system: Optional system prompt.

        Returns:
            Model response or empty string if disabled/error.
        """
        return await self._call_model("sonnet", prompt, system)

    async def call_opus(self, prompt: str, system: str = "") -> str:
        """
        Call Claude Opus model.

        Highest capability model for complex tasks.

        Args:
            prompt: User prompt.
            system: Optional system prompt.

        Returns:
            Model response or empty string if disabled/error.
        """
        return await self._call_model("opus", prompt, system)
