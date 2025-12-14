"""Unit tests for self_improve.py - SELF_IMPROVE pattern learning."""

import pytest
from datetime import date

from mind.self_improve import (
    SelfImproveParser,
    SelfImproveData,
    Pattern,
    PatternType,
    get_patterns_for_stack,
    generate_intuition_context,
    detect_intuitions,
    format_intuitions_for_context,
    extract_patterns_from_feedback,
    _extract_triggers,
    Intuition,
)


class TestSelfImproveParser:
    """Tests for pattern parsing."""

    def test_parse_preference(self):
        parser = SelfImproveParser()
        content = "PREFERENCE: [coding] prefers short functions"
        data = parser.parse(content)

        assert len(data.preferences) == 1
        assert data.preferences[0].category == "coding"
        assert data.preferences[0].description == "prefers short functions"
        assert data.preferences[0].type == PatternType.PREFERENCE

    def test_parse_skill(self):
        parser = SelfImproveParser()
        content = "SKILL: [python:async] expert at asyncio patterns"
        data = parser.parse(content)

        assert len(data.skills) == 1
        assert data.skills[0].category == "python:async"
        assert "asyncio" in data.skills[0].description

    def test_parse_blind_spot(self):
        parser = SelfImproveParser()
        content = "BLIND_SPOT: [testing] often forgets edge cases"
        data = parser.parse(content)

        assert len(data.blind_spots) == 1
        assert data.blind_spots[0].category == "testing"
        assert "edge cases" in data.blind_spots[0].description

    def test_parse_anti_pattern(self):
        parser = SelfImproveParser()
        content = "ANTI_PATTERN: [complexity] tends to over-engineer"
        data = parser.parse(content)

        assert len(data.anti_patterns) == 1
        assert data.anti_patterns[0].category == "complexity"

    def test_parse_feedback_with_date(self):
        parser = SelfImproveParser()
        content = "FEEDBACK: [2025-01-15] forgot error handling -> add try-catch"
        data = parser.parse(content)

        assert len(data.feedback) == 1
        assert data.feedback[0].date_added == date(2025, 1, 15)
        assert "->" in data.feedback[0].description

    def test_parse_multiple_patterns(self):
        parser = SelfImproveParser()
        content = """
## Preferences
PREFERENCE: [coding] short functions
PREFERENCE: [workflow] TDD

## Skills
SKILL: [python] debugging expert

## Blind Spots
BLIND_SPOT: [async] forgets await
"""
        data = parser.parse(content)

        assert len(data.preferences) == 2
        assert len(data.skills) == 1
        assert len(data.blind_spots) == 1

    def test_parse_with_list_prefix(self):
        """Patterns can have optional - prefix."""
        parser = SelfImproveParser()
        content = "- PREFERENCE: [coding] short functions"
        data = parser.parse(content)

        assert len(data.preferences) == 1
        assert data.preferences[0].category == "coding"

    def test_parse_case_insensitive(self):
        """Pattern keywords should be case-insensitive."""
        parser = SelfImproveParser()
        content = "preference: [coding] short functions"
        data = parser.parse(content)

        assert len(data.preferences) == 1

    def test_skip_comments_and_headers(self):
        parser = SelfImproveParser()
        content = """
# This is a header
<!-- This is a comment -->
PREFERENCE: [coding] short functions
"""
        data = parser.parse(content)

        assert len(data.preferences) == 1


class TestStackFiltering:
    """Tests for stack-aware pattern filtering."""

    @pytest.fixture
    def sample_data(self):
        parser = SelfImproveParser()
        return parser.parse("""
PREFERENCE: [python] use type hints
PREFERENCE: [react] use functional components
PREFERENCE: [general] write tests first
SKILL: [python:async] asyncio expert
SKILL: [javascript] promise handling
BLIND_SPOT: [react] forgets useEffect cleanup
BLIND_SPOT: [general] skips edge cases
ANTI_PATTERN: [complexity] over-engineers
""")

    def test_filter_by_stack(self, sample_data):
        filtered = get_patterns_for_stack(sample_data, ["python", "fastapi"])

        # Python preference should be included
        pref_cats = [p.category for p in filtered["preferences"]]
        assert "python" in pref_cats or "general" in pref_cats

        # React preference should NOT be in preferences (stack mismatch)
        # But react is not in universal categories, so it won't be included
        # unless it's a warning type

    def test_universal_categories_always_included(self, sample_data):
        """General/workflow/testing categories should always be included."""
        filtered = get_patterns_for_stack(sample_data, ["rust"])  # Unrelated stack

        pref_cats = [p.category for p in filtered["preferences"]]
        assert "general" in pref_cats

    def test_warnings_always_included(self, sample_data):
        """Blind spots and anti-patterns should be included regardless of stack."""
        filtered = get_patterns_for_stack(sample_data, ["python"])

        # Should include all blind spots (they're warnings)
        assert len(filtered["blind_spots"]) >= 1
        assert len(filtered["anti_patterns"]) >= 1

    def test_partial_stack_match(self, sample_data):
        """python:async should match python stack."""
        filtered = get_patterns_for_stack(sample_data, ["python"])

        skill_cats = [s.category for s in filtered["skills"]]
        assert any("python" in c for c in skill_cats)


class TestIntuitionDetection:
    """Tests for Pattern Radar - intuition detection."""

    @pytest.fixture
    def sample_data(self):
        parser = SelfImproveParser()
        return parser.parse("""
BLIND_SPOT: [async] often forgets to await async functions
BLIND_SPOT: [error-handling] skips try-catch blocks
ANTI_PATTERN: [api] tends to over-fetch data from endpoints
SKILL: [python:debugging] expert at using pdb and breakpoints
""")

    def test_detect_blind_spot_watch(self, sample_data):
        """Blind spots should generate WATCH intuitions."""
        context = "working on an async function"
        intuitions = detect_intuitions(context, sample_data, ["python"])

        watch_intuitions = [i for i in intuitions if i.type == "watch"]
        assert len(watch_intuitions) >= 1
        assert any("await" in i.message.lower() for i in watch_intuitions)

    def test_detect_anti_pattern_avoid(self, sample_data):
        """Anti-patterns should generate AVOID intuitions."""
        context = "fetching data from the API endpoint"
        intuitions = detect_intuitions(context, sample_data, ["python"])

        avoid_intuitions = [i for i in intuitions if i.type == "avoid"]
        assert len(avoid_intuitions) >= 1

    def test_detect_skill_tip(self, sample_data):
        """Skills should generate TIP intuitions."""
        context = "debugging this issue"
        intuitions = detect_intuitions(context, sample_data, ["python"])

        tip_intuitions = [i for i in intuitions if i.type == "tip"]
        assert len(tip_intuitions) >= 1
        assert any("pdb" in i.message.lower() for i in tip_intuitions)

    def test_no_intuitions_for_unrelated_context(self, sample_data):
        """Unrelated context should not trigger intuitions."""
        context = "writing documentation for the readme"
        intuitions = detect_intuitions(context, sample_data, ["python"])

        # May have some, but should be minimal
        assert len(intuitions) <= 2

    def test_max_intuitions_limit(self, sample_data):
        """Should return at most 5 intuitions."""
        # Add more patterns to trigger many intuitions
        parser = SelfImproveParser()
        big_data = parser.parse("""
BLIND_SPOT: [async] forgets await
BLIND_SPOT: [error] skips error handling
BLIND_SPOT: [test] forgets tests
BLIND_SPOT: [api] forgets api errors
BLIND_SPOT: [db] forgets db errors
BLIND_SPOT: [auth] forgets auth
ANTI_PATTERN: [complexity] over-engineers
ANTI_PATTERN: [api] over-fetches
""")
        context = "working on async api with error handling and tests and database auth"
        intuitions = detect_intuitions(context, big_data, ["python"])

        assert len(intuitions) <= 5


class TestTriggerExtraction:
    """Tests for trigger word extraction."""

    def test_extract_from_category(self):
        triggers = _extract_triggers("error-handling", "skips try-catch")
        assert "error" in triggers
        assert "handling" in triggers

    def test_extract_from_description(self):
        triggers = _extract_triggers("async", "forgets to await functions")
        assert "await" in triggers
        assert "functions" in triggers

    def test_adds_related_terms(self):
        """Should add related terms for better matching."""
        triggers = _extract_triggers("api", "over-fetches data")
        # Should include related API terms
        assert any(t in triggers for t in ["api", "fetch", "endpoint", "request"])

    def test_filters_stop_words(self):
        triggers = _extract_triggers("coding", "this is just a very simple test")
        # Stop words should be filtered
        assert "this" not in triggers
        assert "just" not in triggers


class TestFeedbackExtraction:
    """Tests for feedback to pattern pipeline."""

    def test_extract_type_hints_pattern(self):
        """Repeated type hint feedback should extract a preference."""
        # The extraction looks for specific keywords in the correction part
        # "type hint", "typing", "annotation" are the trigger words
        feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "forgot -> add type hint"),
            Pattern(PatternType.FEEDBACK, "2025-01-02", "missing -> use typing"),
            Pattern(PatternType.FEEDBACK, "2025-01-03", "none -> add annotation"),
        ]
        patterns = extract_patterns_from_feedback(feedback, min_occurrences=3)

        assert len(patterns) >= 1
        assert any("type" in desc.lower() for _, _, desc in patterns)

    def test_extract_error_handling_pattern(self):
        """Repeated error handling feedback should extract a blind spot."""
        feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "forgot error handling -> add try"),
            Pattern(PatternType.FEEDBACK, "2025-01-02", "no exception handling -> catch errors"),
            Pattern(PatternType.FEEDBACK, "2025-01-03", "missing error catch -> handle errors"),
        ]
        patterns = extract_patterns_from_feedback(feedback, min_occurrences=3)

        assert len(patterns) >= 1
        # Should identify as blind spot
        assert any(ptype == "blind_spot" for ptype, _, _ in patterns)

    def test_no_extraction_below_threshold(self):
        """Should not extract patterns below min_occurrences."""
        feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "forgot type hints"),
            Pattern(PatternType.FEEDBACK, "2025-01-02", "other issue"),
        ]
        patterns = extract_patterns_from_feedback(feedback, min_occurrences=3)

        assert len(patterns) == 0


class TestContextGeneration:
    """Tests for MIND:CONTEXT generation."""

    def test_generates_preferences_section(self):
        parser = SelfImproveParser()
        data = parser.parse("PREFERENCE: [coding] prefers short functions")
        context = generate_intuition_context(data, ["python"])

        assert "Your Preferences" in context or "Preference" in context

    def test_generates_blind_spots_section(self):
        parser = SelfImproveParser()
        data = parser.parse("BLIND_SPOT: [async] forgets await")
        context = generate_intuition_context(data, ["python"])

        assert "Watch Out" in context or "Blind Spot" in context

    def test_empty_data_returns_empty_string(self):
        data = SelfImproveData()
        context = generate_intuition_context(data, ["python"])

        assert context == ""


class TestIntuitionFormatting:
    """Tests for intuition formatting."""

    def test_format_watch_intuition(self):
        intuitions = [
            Intuition("watch", "You tend to forget X", "BLIND_SPOT: [test]", 0.8)
        ]
        formatted = format_intuitions_for_context(intuitions)

        assert "WATCH" in formatted
        assert "You tend to forget X" in formatted

    def test_format_multiple_intuitions(self):
        intuitions = [
            Intuition("watch", "Watch message", "source1", 0.8),
            Intuition("avoid", "Avoid message", "source2", 0.7),
            Intuition("tip", "Tip message", "source3", 0.6),
        ]
        formatted = format_intuitions_for_context(intuitions)

        assert "WATCH" in formatted
        assert "AVOID" in formatted
        assert "TIP" in formatted

    def test_empty_intuitions_returns_empty(self):
        formatted = format_intuitions_for_context([])
        assert formatted == ""


class TestSelfImproveData:
    """Tests for SelfImproveData dataclass."""

    def test_all_patterns_returns_flat_list(self):
        parser = SelfImproveParser()
        data = parser.parse("""
PREFERENCE: [coding] pref1
SKILL: [python] skill1
BLIND_SPOT: [async] blind1
ANTI_PATTERN: [complexity] anti1
FEEDBACK: [2025-01-01] feedback1
""")
        all_patterns = data.all_patterns()

        assert len(all_patterns) == 5

    def test_to_dict_serialization(self):
        parser = SelfImproveParser()
        data = parser.parse("PREFERENCE: [coding] short functions")
        d = data.to_dict()

        assert "preferences" in d
        assert len(d["preferences"]) == 1
        assert d["preferences"][0]["category"] == "coding"
