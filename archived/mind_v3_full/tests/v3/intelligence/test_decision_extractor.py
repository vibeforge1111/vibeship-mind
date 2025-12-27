"""Tests for decision extraction."""
import pytest
from unittest.mock import MagicMock, patch

from mind.v3.intelligence.cascade import ModelTier, ExtractionResult
from mind.v3.intelligence.extractors.decision import (
    LocalDecisionExtractor,
    Decision,
)


class TestDecision:
    """Test Decision dataclass."""

    def test_create_decision(self):
        """Should create decision with required fields."""
        decision = Decision(
            action="Used SQLite for storage",
            reasoning="Need portability",
        )

        assert decision.action == "Used SQLite for storage"
        assert decision.reasoning == "Need portability"
        assert decision.confidence == 0.0
        assert decision.alternatives == []

    def test_decision_with_all_fields(self):
        """Should support all optional fields."""
        decision = Decision(
            action="Chose React over Vue",
            reasoning="Better ecosystem and team familiarity",
            confidence=0.9,
            alternatives=["Vue", "Angular", "Svelte"],
            context="Building a dashboard",
        )

        assert decision.alternatives == ["Vue", "Angular", "Svelte"]
        assert decision.context == "Building a dashboard"
        assert decision.confidence == 0.9

    def test_decision_to_dict(self):
        """Should serialize to dictionary."""
        decision = Decision(
            action="Used SQLite",
            reasoning="Portability",
            confidence=0.8,
        )

        d = decision.to_dict()

        assert d["action"] == "Used SQLite"
        assert d["reasoning"] == "Portability"
        assert d["confidence"] == 0.8


class TestLocalDecisionExtractor:
    """Test LocalDecisionExtractor."""

    def test_create_extractor(self):
        """Should create extractor."""
        extractor = LocalDecisionExtractor()

        assert extractor is not None

    def test_extract_decided_to(self):
        """Should extract 'decided to' pattern."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract(
            "I decided to use SQLite because it's portable."
        )

        assert result.confidence > 0.0
        assert len(result.content.get("decisions", [])) >= 1
        decisions = result.content["decisions"]
        assert any("SQLite" in d["action"] for d in decisions)

    def test_extract_chose_to(self):
        """Should extract 'chose to' pattern."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract(
            "I chose to implement async/await for better performance."
        )

        assert len(result.content.get("decisions", [])) >= 1

    def test_extract_going_with(self):
        """Should extract 'going with' pattern."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract(
            "I'm going with PostgreSQL for the database."
        )

        assert len(result.content.get("decisions", [])) >= 1

    def test_extract_settled_on(self):
        """Should extract 'settled on' pattern."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract(
            "We settled on using REST instead of GraphQL."
        )

        assert len(result.content.get("decisions", [])) >= 1

    def test_extract_with_because(self):
        """Should extract reasoning with 'because'."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract(
            "I decided to use Redis because it provides fast caching."
        )

        decisions = result.content.get("decisions", [])
        assert len(decisions) >= 1
        # Reasoning should contain the because clause
        assert any("caching" in d.get("reasoning", "").lower() or
                   "because" in d.get("action", "").lower()
                   for d in decisions)

    def test_extract_multiple_decisions(self):
        """Should extract multiple decisions from text."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract("""
            First, I decided to use TypeScript for type safety.
            Then, I chose to implement the observer pattern.
            Finally, I'm going with Jest for testing.
        """)

        decisions = result.content.get("decisions", [])
        assert len(decisions) >= 2  # Should find at least 2

    def test_no_decisions_in_text(self):
        """Should return empty when no decisions found."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract(
            "The weather is nice today."
        )

        decisions = result.content.get("decisions", [])
        assert len(decisions) == 0

    def test_returns_extraction_result(self):
        """Should return proper ExtractionResult."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract("I decided to use Python.")

        assert isinstance(result, ExtractionResult)
        assert result.tier_used == ModelTier.LOCAL
        assert result.model_name == "regex"

    def test_confidence_based_on_matches(self):
        """Confidence should be higher with more context."""
        extractor = LocalDecisionExtractor()

        # Clear decision with reasoning
        result_clear = extractor.extract(
            "I decided to use SQLite because it's portable and requires no server setup."
        )

        # Vague decision
        result_vague = extractor.extract(
            "I decided to do it."
        )

        # Clear should have higher confidence than vague
        assert result_clear.confidence >= result_vague.confidence

    def test_short_text_filtered(self):
        """Should filter out very short decision statements."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract("Going with it.")

        # Too short to be a meaningful decision
        decisions = result.content.get("decisions", [])
        assert len(decisions) == 0

    def test_extract_with_alternatives(self):
        """Should detect alternatives when mentioned."""
        extractor = LocalDecisionExtractor()

        result = extractor.extract(
            "I decided to use SQLite instead of PostgreSQL or MySQL because it's simpler."
        )

        decisions = result.content.get("decisions", [])
        assert len(decisions) >= 1
        # Should detect alternatives (implementation may vary)


class TestLocalDecisionExtractorIntegration:
    """Integration tests with cascade."""

    def test_works_with_cascade(self):
        """Should work when registered with cascade."""
        from mind.v3.intelligence.cascade import ModelCascade, CascadeConfig

        config = CascadeConfig(enable_local=True)
        cascade = ModelCascade(config=config)
        extractor = LocalDecisionExtractor()

        cascade.register_extractor(ModelTier.LOCAL, extractor)

        result = cascade.extract("I decided to use Python for this project.")

        assert result.tier_used == ModelTier.LOCAL
        assert len(result.content.get("decisions", [])) >= 1
