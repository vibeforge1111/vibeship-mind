"""Unit tests for self_improve.py - SELF_IMPROVE pattern learning."""

import pytest
from datetime import date, datetime, timedelta
from pathlib import Path
import tempfile
import json

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
    # Phase 6-7 imports
    PatternMetadata,
    calculate_decayed_confidence,
    hash_pattern_description,
    load_pattern_metadata,
    save_pattern_metadata,
    reinforce_pattern,
    get_pattern_confidence,
    filter_by_confidence,
    get_confidence_stats,
    # Phase 8 imports
    extract_keywords,
    jaccard_similarity,
    find_similar_patterns,
    detect_contradiction,
    find_contradictions,
    add_pattern_with_contradiction_check,
    OPPOSING_PAIRS,
    # Phase 9 imports
    extract_learning_style_from_feedback,
    generate_learning_style_context,
    promote_learning_styles_from_feedback,
    LEARNING_STYLE_INDICATORS,
    LEARNING_STYLE_DESCRIPTIONS,
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


# =============================================================================
# Phase 6: Confidence Decay Tests
# =============================================================================


class TestConfidenceDecay:
    """Tests for confidence decay calculation (Phase 6)."""

    def test_no_decay_within_period(self):
        """Pattern reinforced recently should not decay."""
        recent = datetime.now() - timedelta(days=5)
        confidence = calculate_decayed_confidence(0.8, recent)

        assert confidence == 0.8  # No decay

    def test_single_period_decay(self):
        """Pattern inactive for 30-59 days should decay once."""
        old = datetime.now() - timedelta(days=35)
        confidence = calculate_decayed_confidence(0.8, old)

        # 0.8 * 0.9^1 = 0.72
        assert 0.71 < confidence < 0.73

    def test_multiple_period_decay(self):
        """Pattern inactive for 90+ days should decay three times."""
        very_old = datetime.now() - timedelta(days=95)
        confidence = calculate_decayed_confidence(0.8, very_old)

        # 0.8 * 0.9^3 = 0.5832
        assert 0.58 < confidence < 0.59

    def test_minimum_confidence_floor(self):
        """Confidence should never go below 0.1."""
        ancient = datetime.now() - timedelta(days=365)  # 1 year old
        confidence = calculate_decayed_confidence(0.5, ancient)

        # Should decay significantly but never below 0.1
        assert confidence >= 0.1

    def test_custom_decay_rate(self):
        """Custom decay rate should apply correctly."""
        old = datetime.now() - timedelta(days=35)

        # 20% decay per period
        confidence = calculate_decayed_confidence(0.8, old, decay_rate=0.2)

        # 0.8 * 0.8^1 = 0.64
        assert 0.63 < confidence < 0.65

    def test_custom_decay_period(self):
        """Custom decay period should change when decay starts."""
        old = datetime.now() - timedelta(days=15)

        # With default 30-day period, no decay yet
        conf_default = calculate_decayed_confidence(0.8, old)
        assert conf_default == 0.8

        # With 7-day period, should have decayed twice
        conf_weekly = calculate_decayed_confidence(0.8, old, decay_period_days=7)
        # 0.8 * 0.9^2 = 0.648
        assert 0.64 < conf_weekly < 0.66


class TestPatternMetadata:
    """Tests for PatternMetadata dataclass."""

    def test_metadata_creation(self):
        """Should create metadata with default values."""
        now = datetime.now().isoformat()
        meta = PatternMetadata(
            pattern_hash="abc123",
            created_at=now,
            last_reinforced=now,
        )

        assert meta.pattern_hash == "abc123"
        assert meta.reinforcement_count == 0
        assert meta.base_confidence == 0.5

    def test_current_confidence_applies_decay(self):
        """current_confidence() should apply decay to base_confidence."""
        old_time = (datetime.now() - timedelta(days=60)).isoformat()
        meta = PatternMetadata(
            pattern_hash="abc123",
            created_at=old_time,
            last_reinforced=old_time,
            base_confidence=0.8,
        )

        # Should be decayed from 0.8
        confidence = meta.current_confidence()
        assert confidence < 0.8
        assert confidence >= 0.1


class TestHashPatternDescription:
    """Tests for pattern hash generation."""

    def test_consistent_hashing(self):
        """Same description should always produce same hash."""
        desc = "prefers short functions"
        hash1 = hash_pattern_description(desc)
        hash2 = hash_pattern_description(desc)

        assert hash1 == hash2

    def test_hash_is_12_chars(self):
        """Hash should be exactly 12 characters."""
        hash_val = hash_pattern_description("any description")
        assert len(hash_val) == 12

    def test_normalization_case_insensitive(self):
        """Hash should be case-insensitive."""
        lower_hash = hash_pattern_description("prefers short functions")
        upper_hash = hash_pattern_description("PREFERS SHORT FUNCTIONS")

        assert lower_hash == upper_hash

    def test_normalization_whitespace(self):
        """Hash should handle whitespace normalization."""
        normal = hash_pattern_description("prefers short functions")
        padded = hash_pattern_description("  prefers short functions  ")

        assert normal == padded


# =============================================================================
# Phase 7: Reinforcement Tracking Tests
# =============================================================================


class TestReinforcement:
    """Tests for pattern reinforcement (Phase 7)."""

    @pytest.fixture
    def temp_mind_dir(self, tmp_path, monkeypatch):
        """Create a temporary global mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()

        # Monkey-patch get_global_mind_dir to return our temp dir
        def mock_get_global_mind_dir():
            return mind_dir

        monkeypatch.setattr(
            "mind.self_improve.get_global_mind_dir",
            mock_get_global_mind_dir
        )
        return mind_dir

    def test_reinforce_new_pattern(self, temp_mind_dir):
        """Reinforcing unknown pattern should create metadata."""
        result = reinforce_pattern("new test pattern")

        assert result["success"] is True
        assert result["reinforcement_count"] == 1
        assert result["new_confidence"] == 0.6  # 0.5 + 0.1 boost

    def test_reinforce_existing_pattern(self, temp_mind_dir):
        """Reinforcing known pattern should boost confidence."""
        # First reinforcement
        reinforce_pattern("test pattern")

        # Second reinforcement
        result = reinforce_pattern("test pattern")

        assert result["reinforcement_count"] == 2
        assert result["new_confidence"] == 0.7  # 0.6 + 0.1 boost

    def test_reinforcement_caps_at_one(self, temp_mind_dir):
        """Confidence should not exceed 1.0."""
        # Reinforce many times
        for _ in range(15):
            result = reinforce_pattern("frequently used pattern")

        assert result["new_confidence"] <= 1.0
        assert result["new_confidence"] == 1.0  # Should cap at 1.0

    def test_reinforcement_resets_decay(self, temp_mind_dir):
        """Reinforcing should reset the last_reinforced timestamp."""
        # Create old metadata manually
        old_time = (datetime.now() - timedelta(days=90)).isoformat()
        old_meta = PatternMetadata(
            pattern_hash=hash_pattern_description("old pattern"),
            created_at=old_time,
            last_reinforced=old_time,
            base_confidence=0.5,
        )
        save_pattern_metadata({old_meta.pattern_hash: old_meta})

        # Verify it would have decayed
        loaded = load_pattern_metadata()
        old_confidence = loaded[old_meta.pattern_hash].current_confidence()
        assert old_confidence < 0.5  # Should be decayed

        # Reinforce it
        reinforce_pattern("old pattern")

        # Now should not be decayed
        loaded = load_pattern_metadata()
        new_confidence = loaded[old_meta.pattern_hash].current_confidence()
        assert new_confidence >= 0.5  # Decay reset


class TestMetadataStorage:
    """Tests for pattern metadata JSON storage."""

    @pytest.fixture
    def temp_mind_dir(self, tmp_path, monkeypatch):
        """Create a temporary global mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()

        def mock_get_global_mind_dir():
            return mind_dir

        monkeypatch.setattr(
            "mind.self_improve.get_global_mind_dir",
            mock_get_global_mind_dir
        )
        return mind_dir

    def test_save_and_load_metadata(self, temp_mind_dir):
        """Should round-trip metadata through JSON."""
        now = datetime.now().isoformat()
        original = {
            "abc123": PatternMetadata(
                pattern_hash="abc123",
                created_at=now,
                last_reinforced=now,
                reinforcement_count=5,
                base_confidence=0.8,
            )
        }

        save_pattern_metadata(original)
        loaded = load_pattern_metadata()

        assert "abc123" in loaded
        assert loaded["abc123"].reinforcement_count == 5
        assert loaded["abc123"].base_confidence == 0.8

    def test_load_empty_file(self, temp_mind_dir):
        """Should return empty dict if file doesn't exist."""
        metadata = load_pattern_metadata()
        assert metadata == {}

    def test_load_corrupted_file(self, temp_mind_dir):
        """Should handle corrupted JSON gracefully."""
        path = temp_mind_dir / "pattern_metadata.json"
        path.write_text("not valid json {{{", encoding="utf-8")

        metadata = load_pattern_metadata()
        assert metadata == {}


class TestFilterByConfidence:
    """Tests for confidence-based filtering."""

    def test_filter_removes_low_confidence(self):
        """Should filter out patterns below threshold."""
        patterns = [
            Pattern(PatternType.PREFERENCE, "test", "high confidence", confidence=0.8),
            Pattern(PatternType.PREFERENCE, "test", "low confidence", confidence=0.2),
            Pattern(PatternType.PREFERENCE, "test", "medium confidence", confidence=0.5),
        ]

        # Note: Without metadata, falls back to pattern.confidence
        filtered = filter_by_confidence(patterns, min_confidence=0.3)

        assert len(filtered) == 2
        assert any(p.description == "high confidence" for p in filtered)
        assert any(p.description == "medium confidence" for p in filtered)
        assert not any(p.description == "low confidence" for p in filtered)


class TestConfidenceStats:
    """Tests for confidence statistics."""

    @pytest.fixture
    def temp_mind_dir(self, tmp_path, monkeypatch):
        """Create a temporary global mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()

        def mock_get_global_mind_dir():
            return mind_dir

        monkeypatch.setattr(
            "mind.self_improve.get_global_mind_dir",
            mock_get_global_mind_dir
        )
        return mind_dir

    def test_empty_stats(self, temp_mind_dir):
        """Should handle empty metadata."""
        stats = get_confidence_stats()

        assert stats["total_patterns"] == 0
        assert stats["avg_confidence"] == 0

    def test_stats_with_patterns(self, temp_mind_dir):
        """Should calculate correct statistics."""
        now = datetime.now().isoformat()
        metadata = {
            "p1": PatternMetadata("p1", now, now, 0, 0.8),
            "p2": PatternMetadata("p2", now, now, 0, 0.5),
            "p3": PatternMetadata("p3", now, now, 0, 0.2),
        }
        save_pattern_metadata(metadata)

        stats = get_confidence_stats()

        assert stats["total_patterns"] == 3
        assert 0.49 < stats["avg_confidence"] < 0.51  # (0.8+0.5+0.2)/3 = 0.5
        assert stats["high_confidence"] == 1  # 0.8
        assert stats["medium_confidence"] == 1  # 0.5
        assert stats["low_confidence"] == 1  # 0.2


# =============================================================================
# Phase 8: Contradiction Detection Tests
# =============================================================================


class TestExtractKeywords:
    """Tests for keyword extraction."""

    def test_extracts_long_words(self):
        """Should extract words 4+ characters."""
        keywords = extract_keywords("I prefer short functions as long ones")
        assert "prefer" not in keywords  # It's a stop word
        assert "short" in keywords
        assert "functions" in keywords
        assert "as" not in keywords  # Too short (2 chars)
        assert "long" in keywords
        assert "ones" in keywords

    def test_filters_stop_words(self):
        """Should filter common stop words."""
        keywords = extract_keywords("this that with from have been like prefer")
        assert len(keywords) == 0  # All stop words

    def test_lowercase_normalization(self):
        """Should lowercase all keywords."""
        keywords = extract_keywords("FUNCTIONS and Classes")
        assert "functions" in keywords
        assert "classes" in keywords
        assert "FUNCTIONS" not in keywords

    def test_empty_string(self):
        """Should handle empty string."""
        keywords = extract_keywords("")
        assert keywords == []


class TestJaccardSimilarity:
    """Tests for Jaccard similarity calculation."""

    def test_identical_sets(self):
        """Identical sets should have similarity 1.0."""
        s1 = {"a", "b", "c"}
        s2 = {"a", "b", "c"}
        assert jaccard_similarity(s1, s2) == 1.0

    def test_disjoint_sets(self):
        """Disjoint sets should have similarity 0.0."""
        s1 = {"a", "b", "c"}
        s2 = {"d", "e", "f"}
        assert jaccard_similarity(s1, s2) == 0.0

    def test_partial_overlap(self):
        """Partial overlap should have intermediate similarity."""
        s1 = {"a", "b", "c"}
        s2 = {"b", "c", "d"}
        # Intersection: {b, c} = 2, Union: {a, b, c, d} = 4
        assert jaccard_similarity(s1, s2) == 0.5

    def test_empty_set(self):
        """Empty set should return 0.0."""
        assert jaccard_similarity(set(), {"a"}) == 0.0
        assert jaccard_similarity({"a"}, set()) == 0.0
        assert jaccard_similarity(set(), set()) == 0.0


class TestFindSimilarPatterns:
    """Tests for similar pattern detection."""

    @pytest.fixture
    def sample_patterns(self):
        return [
            Pattern(PatternType.PREFERENCE, "coding", "prefers short functions"),
            Pattern(PatternType.PREFERENCE, "coding", "likes verbose comments"),
            Pattern(PatternType.SKILL, "python", "expert at debugging async code"),
            Pattern(PatternType.BLIND_SPOT, "testing", "forgets edge cases"),
        ]

    def test_finds_similar_by_keywords(self, sample_patterns):
        """Should find patterns with keyword overlap."""
        similar = find_similar_patterns(
            "prefers short methods and functions",
            sample_patterns,
            similarity_threshold=0.3
        )

        assert len(similar) >= 1
        # Should find the "short functions" pattern
        descriptions = [p.description for p, _ in similar]
        assert any("short" in d and "functions" in d for d in descriptions)

    def test_no_match_below_threshold(self, sample_patterns):
        """Should not return patterns below threshold."""
        similar = find_similar_patterns(
            "completely unrelated topic here",
            sample_patterns,
            similarity_threshold=0.4
        )

        assert len(similar) == 0

    def test_sorted_by_similarity(self, sample_patterns):
        """Results should be sorted by similarity descending."""
        similar = find_similar_patterns(
            "prefers short functions with verbose comments",
            sample_patterns,
            similarity_threshold=0.2
        )

        if len(similar) >= 2:
            scores = [score for _, score in similar]
            assert scores == sorted(scores, reverse=True)


class TestDetectContradiction:
    """Tests for contradiction detection."""

    def test_prefer_vs_avoid(self):
        """Should detect prefer/avoid contradiction."""
        p1 = Pattern(PatternType.PREFERENCE, "style", "prefer verbose comments")
        p2 = Pattern(PatternType.PREFERENCE, "style", "avoid verbose comments")

        assert detect_contradiction(p1, p2) is True
        assert detect_contradiction(p2, p1) is True

    def test_verbose_vs_terse(self):
        """Should detect verbose/terse contradiction."""
        p1 = Pattern(PatternType.PREFERENCE, "style", "likes verbose code")
        p2 = Pattern(PatternType.PREFERENCE, "style", "likes terse code")

        assert detect_contradiction(p1, p2) is True

    def test_always_vs_never(self):
        """Should detect always/never contradiction."""
        p1 = Pattern(PatternType.PREFERENCE, "testing", "always write tests first")
        p2 = Pattern(PatternType.PREFERENCE, "testing", "never write tests first")

        assert detect_contradiction(p1, p2) is True

    def test_no_contradiction_different_topics(self):
        """Should not detect contradiction for unrelated patterns."""
        p1 = Pattern(PatternType.PREFERENCE, "style", "prefer short functions")
        p2 = Pattern(PatternType.SKILL, "python", "expert at debugging")

        assert detect_contradiction(p1, p2) is False

    def test_no_contradiction_compatible(self):
        """Should not detect contradiction for compatible patterns."""
        p1 = Pattern(PatternType.PREFERENCE, "coding", "prefer type hints")
        p2 = Pattern(PatternType.PREFERENCE, "coding", "prefer docstrings")

        assert detect_contradiction(p1, p2) is False


class TestFindContradictions:
    """Tests for finding contradictions across patterns."""

    def test_finds_contradicting_patterns(self):
        """Should find patterns that contradict the new one."""
        existing = [
            Pattern(PatternType.PREFERENCE, "style", "prefer verbose comments"),
            Pattern(PatternType.PREFERENCE, "coding", "prefer functional style"),
        ]

        contradictions = find_contradictions(
            "avoid verbose comments",
            PatternType.PREFERENCE,
            existing
        )

        assert len(contradictions) >= 1
        assert any("verbose" in c["pattern"] for c in contradictions)

    def test_no_contradictions_for_compatible(self):
        """Should return empty list for compatible patterns."""
        existing = [
            Pattern(PatternType.PREFERENCE, "coding", "prefer type hints"),
            Pattern(PatternType.SKILL, "python", "expert at debugging"),
        ]

        contradictions = find_contradictions(
            "prefer unit tests",
            PatternType.PREFERENCE,
            existing
        )

        assert len(contradictions) == 0


class TestAddPatternWithContradictionCheck:
    """Tests for safe pattern addition."""

    @pytest.fixture
    def temp_self_improve(self, tmp_path, monkeypatch):
        """Create a temporary SELF_IMPROVE.md file."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        self_improve = mind_dir / "SELF_IMPROVE.md"
        self_improve.write_text("""# SELF_IMPROVE.md

## Preferences
PREFERENCE: [style] prefer verbose comments

## Skills

## Blind Spots

## Anti-Patterns

## Feedback
""", encoding="utf-8")

        def mock_get_self_improve_path():
            return self_improve

        monkeypatch.setattr(
            "mind.self_improve.get_self_improve_path",
            mock_get_self_improve_path
        )
        return self_improve

    def test_adds_non_conflicting_pattern(self, temp_self_improve):
        """Should add pattern when no conflict exists."""
        result = add_pattern_with_contradiction_check(
            PatternType.PREFERENCE,
            "coding",
            "prefer type hints"
        )

        assert result["success"] is True
        assert result["action"] == "added"

    def test_detects_contradiction(self, temp_self_improve):
        """Should detect and block contradicting pattern."""
        result = add_pattern_with_contradiction_check(
            PatternType.PREFERENCE,
            "style",
            "avoid verbose comments"
        )

        assert result["success"] is False
        assert result["action"] == "contradiction_detected"
        assert "conflicts" in result
        assert len(result["conflicts"]) >= 1

    def test_detects_duplicate(self, temp_self_improve):
        """Should detect exact duplicates."""
        result = add_pattern_with_contradiction_check(
            PatternType.PREFERENCE,
            "style",
            "prefer verbose comments"  # Already exists
        )

        assert result["success"] is False
        assert result["action"] == "duplicate"


# =============================================================================
# Phase 9: Learning Style Tests
# =============================================================================


class TestLearningStyleParser:
    """Tests for parsing LEARNING_STYLE patterns."""

    def test_parse_learning_style(self):
        """Should parse LEARNING_STYLE patterns."""
        parser = SelfImproveParser()
        data = parser.parse("LEARNING_STYLE: [debugging] prefers adding logs first")

        assert len(data.learning_styles) == 1
        assert data.learning_styles[0].category == "debugging"
        assert "adding logs" in data.learning_styles[0].description

    def test_parse_multiple_learning_styles(self):
        """Should parse multiple learning styles."""
        parser = SelfImproveParser()
        data = parser.parse("""
LEARNING_STYLE: [concepts] needs concrete examples first
LEARNING_STYLE: [communication] prefers terse explanations
LEARNING_STYLE: [complexity] learns incrementally
""")

        assert len(data.learning_styles) == 3
        categories = [ls.category for ls in data.learning_styles]
        assert "concepts" in categories
        assert "communication" in categories
        assert "complexity" in categories

    def test_learning_style_in_all_patterns(self):
        """Learning styles should appear in all_patterns()."""
        parser = SelfImproveParser()
        data = parser.parse("""
PREFERENCE: [coding] prefers type hints
LEARNING_STYLE: [debugging] logs first
""")

        all_patterns = data.all_patterns()
        assert len(all_patterns) == 2
        types = [p.type for p in all_patterns]
        assert PatternType.PREFERENCE in types
        assert PatternType.LEARNING_STYLE in types

    def test_learning_style_to_dict(self):
        """Learning styles should be included in to_dict()."""
        parser = SelfImproveParser()
        data = parser.parse("LEARNING_STYLE: [concepts] example first")
        d = data.to_dict()

        assert "learning_styles" in d
        assert len(d["learning_styles"]) == 1
        assert d["learning_styles"][0]["category"] == "concepts"


class TestExtractLearningStyleFromFeedback:
    """Tests for extracting learning styles from feedback."""

    def test_extract_example_first_style(self):
        """Should detect preference for examples."""
        feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "too abstract -> show me an example"),
            Pattern(PatternType.FEEDBACK, "2025-01-02", "confused -> can you demonstrate"),
            Pattern(PatternType.FEEDBACK, "2025-01-03", "still unclear -> give example please"),
        ]

        styles = extract_learning_style_from_feedback(feedback)

        assert len(styles) >= 1
        assert any("example" in s[2].lower() for s in styles)

    def test_extract_terse_style(self):
        """Should detect preference for terse communication."""
        feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "too much info"),
            Pattern(PatternType.FEEDBACK, "2025-01-02", "response too long"),
            Pattern(PatternType.FEEDBACK, "2025-01-03", "can you be shorter?"),
        ]

        styles = extract_learning_style_from_feedback(feedback)

        assert len(styles) >= 1
        assert any("terse" in s[2].lower() or "brief" in s[2].lower() for s in styles)

    def test_extract_incremental_style(self):
        """Should detect preference for step-by-step."""
        feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "break it down please"),
            Pattern(PatternType.FEEDBACK, "2025-01-02", "step by step would help"),
        ]

        styles = extract_learning_style_from_feedback(feedback)

        assert len(styles) >= 1
        assert any("incremental" in s[2].lower() or "step" in s[2].lower() for s in styles)

    def test_no_extraction_below_threshold(self):
        """Should not extract with fewer than min occurrences."""
        feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "show me an example"),
            # Only one occurrence
        ]

        styles = extract_learning_style_from_feedback(feedback, min_occurrences=2)

        assert len(styles) == 0

    def test_custom_min_occurrences(self):
        """Should respect custom min_occurrences."""
        feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "show me an example"),
        ]

        # With threshold of 1, should extract
        styles = extract_learning_style_from_feedback(feedback, min_occurrences=1)

        assert len(styles) >= 1


class TestGenerateLearningStyleContext:
    """Tests for generating learning style context."""

    def test_generate_context_with_styles(self):
        """Should generate context section with learning styles."""
        learning_styles = [
            Pattern(PatternType.LEARNING_STYLE, "debugging", "adds logging first"),
            Pattern(PatternType.LEARNING_STYLE, "concepts", "needs examples first"),
        ]

        context = generate_learning_style_context(learning_styles)

        assert "How You Learn Best" in context
        assert "debugging" in context
        assert "adds logging first" in context
        assert "concepts" in context
        assert "needs examples first" in context

    def test_generate_empty_context(self):
        """Should return empty string for no learning styles."""
        context = generate_learning_style_context([])
        assert context == ""

    def test_context_has_adaptation_hint(self):
        """Context should include hint to adapt explanations."""
        learning_styles = [
            Pattern(PatternType.LEARNING_STYLE, "concepts", "example first"),
        ]

        context = generate_learning_style_context(learning_styles)

        assert "Adapt" in context


class TestPromoteLearningStylesFromFeedback:
    """Tests for promoting learning styles from feedback."""

    def test_promotes_new_styles(self):
        """Should create patterns for detected styles."""
        data = SelfImproveData()
        data.feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "show me an example"),
            Pattern(PatternType.FEEDBACK, "2025-01-02", "can you demonstrate"),
            Pattern(PatternType.FEEDBACK, "2025-01-03", "give example please"),
        ]

        new_patterns = promote_learning_styles_from_feedback(data)

        assert len(new_patterns) >= 1
        assert all(p.type == PatternType.LEARNING_STYLE for p in new_patterns)

    def test_doesnt_duplicate_existing(self):
        """Should not create duplicates of existing styles."""
        data = SelfImproveData()
        data.feedback = [
            Pattern(PatternType.FEEDBACK, "2025-01-01", "show me an example"),
            Pattern(PatternType.FEEDBACK, "2025-01-02", "can you demonstrate"),
        ]
        # Already has this style
        data.learning_styles = [
            Pattern(PatternType.LEARNING_STYLE, "concepts",
                   "learns better with concrete examples before abstract explanations"),
        ]

        new_patterns = promote_learning_styles_from_feedback(data)

        # Should not promote the example_first style since it already exists
        assert len(new_patterns) == 0
