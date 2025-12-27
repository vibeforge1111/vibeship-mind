"""Tests for intelligence levels configuration."""
import pytest

from mind.v3.api.levels import IntelligenceLevel, LEVELS, get_level


class TestIntelligenceLevelDataclass:
    """Tests for IntelligenceLevel dataclass."""

    def test_intelligence_level_has_all_required_fields(self):
        """Test IntelligenceLevel has all required fields."""
        level = IntelligenceLevel(
            name="TEST",
            description="Test level",
            extraction_model="haiku",
            reranking_model="sonnet",
            summary_model="opus",
            estimated_cost="~$10/mo",
        )

        assert level.name == "TEST"
        assert level.description == "Test level"
        assert level.extraction_model == "haiku"
        assert level.reranking_model == "sonnet"
        assert level.summary_model == "opus"
        assert level.estimated_cost == "~$10/mo"

    def test_intelligence_level_allows_none_for_models(self):
        """Test IntelligenceLevel allows None for model fields."""
        level = IntelligenceLevel(
            name="FREE",
            description="No API calls",
            extraction_model=None,
            reranking_model=None,
            summary_model=None,
            estimated_cost="$0/mo",
        )

        assert level.extraction_model is None
        assert level.reranking_model is None
        assert level.summary_model is None


class TestLEVELSDict:
    """Tests for the LEVELS dictionary."""

    def test_levels_contains_all_five_levels(self):
        """Test LEVELS dict has all 5 intelligence levels."""
        expected_levels = ["FREE", "LITE", "BALANCED", "PRO", "ULTRA"]

        for level_name in expected_levels:
            assert level_name in LEVELS, f"Missing level: {level_name}"

        assert len(LEVELS) == 5

    def test_free_level_configuration(self):
        """Test FREE level has no API models."""
        free = LEVELS["FREE"]

        assert free.name == "FREE"
        assert free.extraction_model is None
        assert free.reranking_model is None
        assert free.summary_model is None
        assert "$0" in free.estimated_cost

    def test_lite_level_configuration(self):
        """Test LITE level uses haiku for extraction only."""
        lite = LEVELS["LITE"]

        assert lite.name == "LITE"
        assert lite.extraction_model == "haiku"
        assert lite.reranking_model is None
        assert lite.summary_model is None
        assert "$" in lite.estimated_cost

    def test_balanced_level_configuration(self):
        """Test BALANCED level uses haiku for extraction, haiku for reranking, sonnet for summary."""
        balanced = LEVELS["BALANCED"]

        assert balanced.name == "BALANCED"
        assert balanced.extraction_model == "haiku"
        assert balanced.reranking_model == "haiku"
        assert balanced.summary_model == "sonnet"
        assert "$" in balanced.estimated_cost

    def test_pro_level_configuration(self):
        """Test PRO level uses haiku for extraction, sonnet for reranking, sonnet for summary."""
        pro = LEVELS["PRO"]

        assert pro.name == "PRO"
        assert pro.extraction_model == "haiku"
        assert pro.reranking_model == "sonnet"
        assert pro.summary_model == "sonnet"
        assert "$" in pro.estimated_cost

    def test_ultra_level_configuration(self):
        """Test ULTRA level uses sonnet for extraction, opus for reranking, opus for summary."""
        ultra = LEVELS["ULTRA"]

        assert ultra.name == "ULTRA"
        assert ultra.extraction_model == "sonnet"
        assert ultra.reranking_model == "opus"
        assert ultra.summary_model == "opus"
        assert "$" in ultra.estimated_cost

    def test_all_levels_are_intelligence_level_instances(self):
        """Test all LEVELS values are IntelligenceLevel instances."""
        for name, level in LEVELS.items():
            assert isinstance(level, IntelligenceLevel), f"{name} is not an IntelligenceLevel"

    def test_all_levels_have_estimated_cost_with_dollar_sign(self):
        """Test all levels have estimated_cost containing $."""
        for name, level in LEVELS.items():
            assert "$" in level.estimated_cost, f"{name} missing $ in estimated_cost"

    def test_all_levels_have_non_empty_description(self):
        """Test all levels have a non-empty description."""
        for name, level in LEVELS.items():
            assert level.description, f"{name} has empty description"
            assert len(level.description) > 0


class TestGetLevel:
    """Tests for get_level() function."""

    def test_get_level_returns_correct_level(self):
        """Test get_level returns the correct IntelligenceLevel."""
        for level_name in ["FREE", "LITE", "BALANCED", "PRO", "ULTRA"]:
            level = get_level(level_name)
            assert level.name == level_name

    def test_get_level_case_insensitive(self):
        """Test get_level works with different cases."""
        assert get_level("free").name == "FREE"
        assert get_level("Free").name == "FREE"
        assert get_level("FREE").name == "FREE"
        assert get_level("lite").name == "LITE"
        assert get_level("Lite").name == "LITE"
        assert get_level("LITE").name == "LITE"
        assert get_level("balanced").name == "BALANCED"
        assert get_level("Balanced").name == "BALANCED"
        assert get_level("pro").name == "PRO"
        assert get_level("ultra").name == "ULTRA"

    def test_get_level_returns_free_for_invalid_name(self):
        """Test get_level returns FREE for invalid names."""
        assert get_level("invalid").name == "FREE"
        assert get_level("").name == "FREE"
        assert get_level("SUPER").name == "FREE"
        assert get_level("basic").name == "FREE"
        assert get_level("nonexistent").name == "FREE"

    def test_get_level_returns_free_for_whitespace(self):
        """Test get_level returns FREE for whitespace input."""
        assert get_level(" ").name == "FREE"
        assert get_level("  FREE  ").name == "FREE"  # Note: may need to handle strips

    def test_get_level_returns_intelligence_level_instance(self):
        """Test get_level always returns IntelligenceLevel instance."""
        for name in ["FREE", "LITE", "BALANCED", "PRO", "ULTRA", "invalid"]:
            level = get_level(name)
            assert isinstance(level, IntelligenceLevel)


class TestLevelCostProgression:
    """Tests for cost progression across levels."""

    def test_levels_have_increasing_capability(self):
        """Test levels progress from less to more capable (by model usage)."""
        free = LEVELS["FREE"]
        lite = LEVELS["LITE"]
        balanced = LEVELS["BALANCED"]
        pro = LEVELS["PRO"]
        ultra = LEVELS["ULTRA"]

        # FREE has no models
        assert free.extraction_model is None

        # LITE has extraction only
        assert lite.extraction_model is not None
        assert lite.reranking_model is None

        # BALANCED has extraction and reranking
        assert balanced.extraction_model is not None
        assert balanced.reranking_model is not None
        assert balanced.summary_model is not None

        # PRO has all with better reranking
        assert pro.extraction_model is not None
        assert pro.reranking_model is not None
        assert pro.summary_model is not None

        # ULTRA uses most capable models
        assert ultra.extraction_model == "sonnet"  # Better than haiku
        assert ultra.reranking_model == "opus"  # Best
        assert ultra.summary_model == "opus"  # Best
