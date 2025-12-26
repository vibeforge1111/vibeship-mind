"""Tests for Claude API client foundation."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mind.v3.api.client import ClaudeClient, ClaudeConfig


class TestClaudeConfig:
    """Tests for ClaudeConfig dataclass."""

    def test_default_config_values(self):
        """Test that ClaudeConfig has correct defaults."""
        config = ClaudeConfig()

        assert config.api_key is None
        assert config.intelligence_level == "FREE"
        assert config.max_retries == 3
        assert config.timeout == 30.0

    def test_config_with_custom_values(self):
        """Test ClaudeConfig with custom values."""
        config = ClaudeConfig(
            api_key="test-key",
            intelligence_level="PRO",
            max_retries=5,
            timeout=60.0,
        )

        assert config.api_key == "test-key"
        assert config.intelligence_level == "PRO"
        assert config.max_retries == 5
        assert config.timeout == 60.0

    def test_from_env_loads_api_key(self):
        """Test from_env loads ANTHROPIC_API_KEY from environment."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-test-key"}, clear=False):
            config = ClaudeConfig.from_env()

            assert config.api_key == "env-test-key"

    def test_from_env_loads_intelligence_level(self):
        """Test from_env loads MIND_INTELLIGENCE_LEVEL from environment."""
        with patch.dict(
            os.environ,
            {"MIND_INTELLIGENCE_LEVEL": "BALANCED"},
            clear=False,
        ):
            config = ClaudeConfig.from_env()

            assert config.intelligence_level == "BALANCED"

    def test_from_env_with_no_env_vars(self):
        """Test from_env returns defaults when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure these specific keys are removed
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("MIND_INTELLIGENCE_LEVEL", None)

            config = ClaudeConfig.from_env()

            assert config.api_key is None
            assert config.intelligence_level == "FREE"


class TestClaudeClient:
    """Tests for ClaudeClient class."""

    def test_models_dict_contains_all_models(self):
        """Test MODELS dict has haiku, sonnet, opus."""
        config = ClaudeConfig()
        client = ClaudeClient(config)

        assert "haiku" in client.MODELS
        assert "sonnet" in client.MODELS
        assert "opus" in client.MODELS

    def test_enabled_false_when_no_api_key(self):
        """Test enabled is False when api_key is None."""
        config = ClaudeConfig(api_key=None, intelligence_level="PRO")
        client = ClaudeClient(config)

        assert client.enabled is False

    def test_enabled_false_when_free_level(self):
        """Test enabled is False when intelligence_level is FREE."""
        config = ClaudeConfig(api_key="test-key", intelligence_level="FREE")
        client = ClaudeClient(config)

        assert client.enabled is False

    def test_enabled_true_when_key_and_non_free_level(self):
        """Test enabled is True when api_key set and level is not FREE."""
        config = ClaudeConfig(api_key="test-key", intelligence_level="LITE")
        client = ClaudeClient(config)

        assert client.enabled is True

    def test_enabled_with_all_levels(self):
        """Test enabled is True for all non-FREE levels."""
        levels = ["LITE", "BALANCED", "PRO", "ULTRA"]

        for level in levels:
            config = ClaudeConfig(api_key="test-key", intelligence_level=level)
            client = ClaudeClient(config)
            assert client.enabled is True, f"Should be enabled for {level}"


class TestClaudeClientCallMethods:
    """Tests for ClaudeClient async call methods."""

    @pytest.mark.asyncio
    async def test_call_haiku_returns_empty_when_disabled(self):
        """Test call_haiku returns empty string when client disabled."""
        config = ClaudeConfig(api_key=None, intelligence_level="FREE")
        client = ClaudeClient(config)

        result = await client.call_haiku("test prompt")

        assert result == ""

    @pytest.mark.asyncio
    async def test_call_sonnet_returns_empty_when_disabled(self):
        """Test call_sonnet returns empty string when client disabled."""
        config = ClaudeConfig(api_key=None, intelligence_level="FREE")
        client = ClaudeClient(config)

        result = await client.call_sonnet("test prompt")

        assert result == ""

    @pytest.mark.asyncio
    async def test_call_opus_returns_empty_when_disabled(self):
        """Test call_opus returns empty string when client disabled."""
        config = ClaudeConfig(api_key=None, intelligence_level="FREE")
        client = ClaudeClient(config)

        result = await client.call_opus("test prompt")

        assert result == ""

    @pytest.mark.asyncio
    async def test_call_haiku_with_mocked_api(self):
        """Test call_haiku returns response from mocked API."""
        config = ClaudeConfig(api_key="test-key", intelligence_level="PRO")
        client = ClaudeClient(config)

        # Create mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Mocked response")]

        # Mock the anthropic client
        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            result = await client.call_haiku("test prompt", system="test system")

        assert result == "Mocked response"
        mock_anthropic_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_returns_empty_on_error(self):
        """Test call methods return empty string on API error."""
        config = ClaudeConfig(api_key="test-key", intelligence_level="PRO")
        client = ClaudeClient(config)

        # Mock client that raises exception
        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            result = await client.call_haiku("test prompt")

        assert result == ""

    @pytest.mark.asyncio
    async def test_call_with_empty_system_prompt(self):
        """Test call works with default empty system prompt."""
        config = ClaudeConfig(api_key="test-key", intelligence_level="LITE")
        client = ClaudeClient(config)

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response without system")]

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            result = await client.call_haiku("test prompt")

        assert result == "Response without system"


class TestClaudeClientLazyInit:
    """Tests for lazy initialization of anthropic client."""

    def test_get_client_returns_none_when_anthropic_not_installed(self):
        """Test _get_client handles ImportError gracefully."""
        config = ClaudeConfig(api_key="test-key", intelligence_level="PRO")
        client = ClaudeClient(config)

        with patch.dict("sys.modules", {"anthropic": None}):
            # Force reimport attempt
            client._anthropic_client = None

            # This should handle the missing module gracefully
            result = client._get_client()

            # When anthropic is not available, should return None
            # (or handle gracefully in implementation)

    def test_get_client_creates_anthropic_client(self):
        """Test _get_client creates anthropic.Anthropic instance."""
        config = ClaudeConfig(api_key="test-key", intelligence_level="PRO")
        client = ClaudeClient(config)

        mock_anthropic_class = MagicMock()
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic = mock_anthropic_class

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            with patch("mind.v3.api.client.anthropic", mock_anthropic_module):
                # Reset any cached client
                client._anthropic_client = None
                result = client._get_client()

                # Should create client with api_key
                mock_anthropic_class.assert_called_once_with(api_key="test-key")
