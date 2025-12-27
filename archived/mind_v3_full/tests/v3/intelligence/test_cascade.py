"""Tests for model cascade routing."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from mind.v3.intelligence.cascade import (
    ModelTier,
    ModelCascade,
    CascadeConfig,
    ExtractionResult,
)


class TestModelTier:
    """Test ModelTier enum."""

    def test_tier_values(self):
        """Should have expected tier values."""
        assert ModelTier.LOCAL.value == "local"
        assert ModelTier.FAST_API.value == "fast_api"
        assert ModelTier.POWERFUL_API.value == "powerful_api"

    def test_tier_ordering(self):
        """Tiers should be ordered by capability."""
        tiers = list(ModelTier)
        assert tiers[0] == ModelTier.LOCAL
        assert tiers[1] == ModelTier.FAST_API
        assert tiers[2] == ModelTier.POWERFUL_API


class TestCascadeConfig:
    """Test CascadeConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = CascadeConfig()

        assert config.enable_local is True
        assert config.enable_fast_api is False  # Off by default (needs API key)
        assert config.enable_powerful_api is False
        assert config.local_confidence_threshold == 0.7
        assert config.fast_api_confidence_threshold == 0.85

    def test_custom_config(self):
        """Should accept custom settings."""
        config = CascadeConfig(
            enable_fast_api=True,
            local_confidence_threshold=0.8,
        )

        assert config.enable_fast_api is True
        assert config.local_confidence_threshold == 0.8


class TestExtractionResult:
    """Test ExtractionResult dataclass."""

    def test_create_result(self):
        """Should create result with all fields."""
        result = ExtractionResult(
            content={"decision": "Used SQLite"},
            confidence=0.85,
            tier_used=ModelTier.LOCAL,
            model_name="regex",
        )

        assert result.content == {"decision": "Used SQLite"}
        assert result.confidence == 0.85
        assert result.tier_used == ModelTier.LOCAL
        assert result.model_name == "regex"

    def test_result_with_metadata(self):
        """Should support optional metadata."""
        result = ExtractionResult(
            content={"decision": "Used SQLite"},
            confidence=0.9,
            tier_used=ModelTier.FAST_API,
            model_name="haiku",
            metadata={"tokens_used": 150},
        )

        assert result.metadata["tokens_used"] == 150


class TestModelCascade:
    """Test ModelCascade routing logic."""

    def test_create_cascade(self):
        """Should create cascade with config."""
        cascade = ModelCascade()

        assert cascade.config is not None
        assert cascade.config.enable_local is True

    def test_create_cascade_with_config(self):
        """Should accept custom config."""
        config = CascadeConfig(enable_fast_api=True)
        cascade = ModelCascade(config=config)

        assert cascade.config.enable_fast_api is True

    def test_get_available_tiers_local_only(self):
        """Should return only local tier when APIs disabled."""
        config = CascadeConfig(
            enable_local=True,
            enable_fast_api=False,
            enable_powerful_api=False,
        )
        cascade = ModelCascade(config=config)

        tiers = cascade.get_available_tiers()

        assert tiers == [ModelTier.LOCAL]

    def test_get_available_tiers_all(self):
        """Should return all enabled tiers."""
        config = CascadeConfig(
            enable_local=True,
            enable_fast_api=True,
            enable_powerful_api=True,
        )
        cascade = ModelCascade(config=config)

        tiers = cascade.get_available_tiers()

        assert ModelTier.LOCAL in tiers
        assert ModelTier.FAST_API in tiers
        assert ModelTier.POWERFUL_API in tiers

    def test_should_escalate_low_confidence(self):
        """Should escalate when confidence is below threshold."""
        config = CascadeConfig(enable_fast_api=True)  # Need a tier to escalate to
        cascade = ModelCascade(config=config)

        result = ExtractionResult(
            content={},
            confidence=0.5,  # Below 0.7 threshold
            tier_used=ModelTier.LOCAL,
            model_name="regex",
        )

        assert cascade.should_escalate(result) is True

    def test_should_not_escalate_high_confidence(self):
        """Should not escalate when confidence is above threshold."""
        cascade = ModelCascade()

        result = ExtractionResult(
            content={"decision": "clear decision"},
            confidence=0.9,  # Above 0.7 threshold
            tier_used=ModelTier.LOCAL,
            model_name="regex",
        )

        assert cascade.should_escalate(result) is False

    def test_should_not_escalate_at_highest_tier(self):
        """Should not escalate when already at highest tier."""
        config = CascadeConfig(enable_powerful_api=True)
        cascade = ModelCascade(config=config)

        result = ExtractionResult(
            content={},
            confidence=0.5,
            tier_used=ModelTier.POWERFUL_API,
            model_name="sonnet",
        )

        assert cascade.should_escalate(result) is False

    def test_get_next_tier(self):
        """Should get next tier in cascade."""
        config = CascadeConfig(
            enable_local=True,
            enable_fast_api=True,
            enable_powerful_api=True,
        )
        cascade = ModelCascade(config=config)

        assert cascade.get_next_tier(ModelTier.LOCAL) == ModelTier.FAST_API
        assert cascade.get_next_tier(ModelTier.FAST_API) == ModelTier.POWERFUL_API
        assert cascade.get_next_tier(ModelTier.POWERFUL_API) is None

    def test_get_next_tier_skips_disabled(self):
        """Should skip disabled tiers."""
        config = CascadeConfig(
            enable_local=True,
            enable_fast_api=False,  # Disabled
            enable_powerful_api=True,
        )
        cascade = ModelCascade(config=config)

        # Should skip fast_api and go to powerful_api
        assert cascade.get_next_tier(ModelTier.LOCAL) == ModelTier.POWERFUL_API


class TestModelCascadeExtraction:
    """Test cascade extraction with extractors."""

    @pytest.fixture
    def cascade_with_extractors(self):
        """Create cascade with mock extractors."""
        config = CascadeConfig(
            enable_local=True,
            enable_fast_api=True,
            enable_powerful_api=False,
        )
        cascade = ModelCascade(config=config)

        # Register mock extractors
        local_extractor = MagicMock()
        local_extractor.extract = MagicMock(return_value=ExtractionResult(
            content={"decision": "unclear"},
            confidence=0.5,
            tier_used=ModelTier.LOCAL,
            model_name="regex",
        ))

        fast_extractor = MagicMock()
        fast_extractor.extract = MagicMock(return_value=ExtractionResult(
            content={"decision": "Used SQLite for portability"},
            confidence=0.9,
            tier_used=ModelTier.FAST_API,
            model_name="haiku",
        ))

        cascade.register_extractor(ModelTier.LOCAL, local_extractor)
        cascade.register_extractor(ModelTier.FAST_API, fast_extractor)

        return cascade

    def test_register_extractor(self, cascade_with_extractors):
        """Should register extractors for tiers."""
        cascade = cascade_with_extractors

        assert ModelTier.LOCAL in cascade.extractors
        assert ModelTier.FAST_API in cascade.extractors

    def test_extract_escalates_on_low_confidence(self, cascade_with_extractors):
        """Should escalate to next tier on low confidence."""
        cascade = cascade_with_extractors

        result = cascade.extract("I decided to use SQLite")

        # Should have escalated to fast_api
        assert result.tier_used == ModelTier.FAST_API
        assert result.confidence == 0.9
        assert "SQLite" in result.content.get("decision", "")

    def test_extract_stops_on_high_confidence(self):
        """Should stop at local tier if confidence is high."""
        config = CascadeConfig(enable_local=True, enable_fast_api=True)
        cascade = ModelCascade(config=config)

        local_extractor = MagicMock()
        local_extractor.extract = MagicMock(return_value=ExtractionResult(
            content={"decision": "Clear decision here"},
            confidence=0.95,  # High confidence
            tier_used=ModelTier.LOCAL,
            model_name="regex",
        ))

        fast_extractor = MagicMock()
        cascade.register_extractor(ModelTier.LOCAL, local_extractor)
        cascade.register_extractor(ModelTier.FAST_API, fast_extractor)

        result = cascade.extract("Clear decision here")

        # Should stop at local, not escalate
        assert result.tier_used == ModelTier.LOCAL
        fast_extractor.extract.assert_not_called()

    def test_extract_returns_best_result_when_no_escalation_possible(self):
        """Should return best result when no more tiers available."""
        config = CascadeConfig(
            enable_local=True,
            enable_fast_api=False,  # Disabled
            enable_powerful_api=False,
        )
        cascade = ModelCascade(config=config)

        local_extractor = MagicMock()
        local_extractor.extract = MagicMock(return_value=ExtractionResult(
            content={"decision": "Maybe decision"},
            confidence=0.4,  # Low but no escalation possible
            tier_used=ModelTier.LOCAL,
            model_name="regex",
        ))

        cascade.register_extractor(ModelTier.LOCAL, local_extractor)

        result = cascade.extract("Maybe decision")

        # Should return local result since no escalation possible
        assert result.tier_used == ModelTier.LOCAL
        assert result.confidence == 0.4
