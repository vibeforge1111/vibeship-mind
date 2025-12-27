"""Tests for pattern detection."""
import pytest

from mind.v3.intelligence.cascade import ModelTier, ExtractionResult
from mind.v3.intelligence.extractors.pattern import (
    Pattern,
    PatternType,
    LocalPatternDetector,
)


class TestPatternType:
    """Test PatternType enum."""

    def test_pattern_types_exist(self):
        """Should have expected pattern types."""
        assert PatternType.PREFERENCE.value == "preference"
        assert PatternType.HABIT.value == "habit"
        assert PatternType.ANTI_PATTERN.value == "anti_pattern"
        assert PatternType.BLIND_SPOT.value == "blind_spot"


class TestPattern:
    """Test Pattern dataclass."""

    def test_create_pattern(self):
        """Should create pattern with required fields."""
        pattern = Pattern(
            description="Prefers functional programming style",
            pattern_type=PatternType.PREFERENCE,
        )

        assert pattern.description == "Prefers functional programming style"
        assert pattern.pattern_type == PatternType.PREFERENCE
        assert pattern.confidence == 0.0

    def test_pattern_with_evidence(self):
        """Should support evidence count."""
        pattern = Pattern(
            description="Always writes tests first",
            pattern_type=PatternType.HABIT,
            confidence=0.9,
            evidence_count=15,
        )

        assert pattern.evidence_count == 15
        assert pattern.confidence == 0.9

    def test_pattern_to_dict(self):
        """Should serialize to dictionary."""
        pattern = Pattern(
            description="Prefers TypeScript",
            pattern_type=PatternType.PREFERENCE,
            confidence=0.8,
        )

        d = pattern.to_dict()

        assert d["description"] == "Prefers TypeScript"
        assert d["type"] == "preference"
        assert d["confidence"] == 0.8


class TestLocalPatternDetector:
    """Test LocalPatternDetector."""

    def test_create_detector(self):
        """Should create detector."""
        detector = LocalPatternDetector()

        assert detector is not None

    def test_detect_preference_prefer(self):
        """Should detect 'prefer' patterns."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "I prefer using TypeScript over JavaScript for type safety."
        )

        patterns = result.content.get("patterns", [])
        assert any(
            p["type"] == "preference" and "TypeScript" in p["description"]
            for p in patterns
        )

    def test_detect_preference_always(self):
        """Should detect 'always' patterns as habits."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "I always write tests before implementing features."
        )

        patterns = result.content.get("patterns", [])
        assert any(p["type"] == "habit" for p in patterns)

    def test_detect_preference_never(self):
        """Should detect 'never' patterns."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "I never use var in JavaScript, only const and let."
        )

        patterns = result.content.get("patterns", [])
        assert len(patterns) >= 1

    def test_detect_habit_usually(self):
        """Should detect 'usually' patterns."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "I usually start with a simple implementation first."
        )

        patterns = result.content.get("patterns", [])
        assert any(p["type"] == "habit" for p in patterns)

    def test_detect_anti_pattern_avoid(self):
        """Should detect 'avoid' anti-patterns."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "I avoid using global variables whenever possible."
        )

        patterns = result.content.get("patterns", [])
        assert any(p["type"] == "anti_pattern" for p in patterns)

    def test_detect_anti_pattern_dont(self):
        """Should detect 'don't' anti-patterns."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "I don't like deeply nested callbacks."
        )

        patterns = result.content.get("patterns", [])
        assert len(patterns) >= 1

    def test_detect_blind_spot_forget(self):
        """Should detect 'forget' blind spots."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "I often forget to handle edge cases in tests."
        )

        patterns = result.content.get("patterns", [])
        assert any(p["type"] == "blind_spot" for p in patterns)

    def test_detect_blind_spot_tend_to(self):
        """Should detect 'tend to' blind spots."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "I tend to over-engineer simple solutions."
        )

        patterns = result.content.get("patterns", [])
        assert any(p["type"] == "blind_spot" for p in patterns)

    def test_detect_multiple_patterns(self):
        """Should detect multiple patterns."""
        detector = LocalPatternDetector()

        result = detector.extract("""
            I prefer TypeScript for type safety.
            I always write tests first.
            I tend to forget error handling.
        """)

        patterns = result.content.get("patterns", [])
        assert len(patterns) >= 2

    def test_no_patterns_in_text(self):
        """Should return empty when no patterns found."""
        detector = LocalPatternDetector()

        result = detector.extract(
            "The function calculates the sum of two numbers."
        )

        patterns = result.content.get("patterns", [])
        assert len(patterns) == 0

    def test_returns_extraction_result(self):
        """Should return proper ExtractionResult."""
        detector = LocalPatternDetector()

        result = detector.extract("I prefer Python.")

        assert isinstance(result, ExtractionResult)
        assert result.tier_used == ModelTier.LOCAL
        assert result.model_name == "regex"

    def test_short_text_filtered(self):
        """Should filter out very short pattern statements."""
        detector = LocalPatternDetector()

        result = detector.extract("I prefer it.")

        patterns = result.content.get("patterns", [])
        assert len(patterns) == 0


class TestLocalPatternDetectorIntegration:
    """Integration tests with cascade."""

    def test_works_with_cascade(self):
        """Should work when registered with cascade."""
        from mind.v3.intelligence.cascade import ModelCascade, CascadeConfig

        config = CascadeConfig(enable_local=True)
        cascade = ModelCascade(config=config)
        detector = LocalPatternDetector()

        cascade.register_extractor(ModelTier.LOCAL, detector)

        result = cascade.extract("I always use async/await for async code.")

        assert result.tier_used == ModelTier.LOCAL
        assert len(result.content.get("patterns", [])) >= 1
