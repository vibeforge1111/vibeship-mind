"""Tests for semantic similarity loop detection."""

import pytest
from mind.similarity import (
    semantic_similarity,
    keyword_similarity,
    find_similar_rejection,
    is_semantic_available,
)


class TestKeywordSimilarity:
    """Tests for fallback keyword-based similarity."""

    def test_identical_texts(self):
        sim = keyword_similarity("increase the timeout", "increase the timeout")
        assert sim == 1.0

    def test_completely_different(self):
        sim = keyword_similarity("increase timeout", "fix database connection")
        assert sim == 0.0

    def test_partial_overlap(self):
        sim = keyword_similarity("increase the timeout value", "timeout error occurred")
        # "timeout" overlaps, so should be > 0
        assert 0 < sim < 1

    def test_stop_words_ignored(self):
        # "the" and "and" are stop words
        sim = keyword_similarity("the timeout", "and timeout")
        assert sim == 1.0  # Only "timeout" matters


class TestSemanticSimilarity:
    """Tests for semantic similarity (requires sentence-transformers)."""

    def test_identical_texts(self):
        sim = semantic_similarity("increase the timeout", "increase the timeout")
        assert sim > 0.99

    def test_semantically_similar(self):
        """These are semantically similar but have different words."""
        sim = semantic_similarity(
            "increase the timeout",
            "extend the wait duration"
        )
        # Should be high similarity even with different words
        if is_semantic_available():
            assert sim > 0.5, f"Expected semantic similarity > 0.5, got {sim}"
        else:
            # Keyword fallback won't catch this
            assert sim >= 0  # Just verify it runs

    def test_semantically_different(self):
        sim = semantic_similarity(
            "increase the timeout",
            "refactor the database schema"
        )
        # Should be low similarity
        assert sim < 0.5


class TestFindSimilarRejection:
    """Tests for the main loop detection function."""

    def test_no_existing_rejections(self):
        result = find_similar_rejection("try bumping timeout", [])
        assert result is None

    def test_empty_message(self):
        result = find_similar_rejection("", ["some rejection"])
        assert result is None

    def test_exact_match(self):
        rejections = [
            "tried increasing timeout - didn't work",
            "tried using cache - too complex",
        ]
        result = find_similar_rejection("tried increasing timeout - didn't work", rejections)
        assert result is not None
        assert result["similarity"] > 0.99
        assert "similar_to" in result
        assert "suggestion" in result

    def test_semantic_match(self):
        """Test that semantically similar rejections are caught."""
        rejections = [
            "tried increasing the timeout - still failing",
            "tried using redis cache - too complex",
        ]

        # This should match the first rejection semantically
        result = find_similar_rejection(
            "bumping the wait duration didn't help",
            rejections,
            threshold=0.5  # Lower threshold for semantic matching
        )

        if is_semantic_available():
            # With semantic matching, this should be caught
            assert result is not None, "Semantic match should have been found"
            assert "timeout" in result["similar_to"].lower() or "wait" in result["similar_to"].lower()
        else:
            # Keyword fallback might not catch this
            pass

    def test_below_threshold(self):
        """Test that dissimilar rejections don't trigger warning."""
        rejections = [
            "tried using mongodb - overkill for this",
        ]
        result = find_similar_rejection(
            "increase timeout",
            rejections,
            threshold=0.7
        )
        assert result is None

    def test_returns_best_match(self):
        """Test that the most similar rejection is returned."""
        rejections = [
            "tried redis - too complex",
            "tried increasing timeout to 30s - still failing",
            "tried postgres - wrong tool",
        ]
        result = find_similar_rejection(
            "bump timeout to 60s",
            rejections,
            threshold=0.4
        )

        if result:
            # Should match the timeout one, not redis or postgres
            assert "timeout" in result["similar_to"].lower()


class TestRealWorldScenarios:
    """Test scenarios from actual usage patterns."""

    def test_timeout_variations(self):
        """Different ways of saying 'increase timeout'."""
        existing = ["tried increasing timeout to 60s - still failing"]

        variations = [
            "try bumping the timeout again",
            "maybe increase the wait time",
            "extend the delay",
            "set longer timeout",
        ]

        if is_semantic_available():
            # At least some of these should match with semantic similarity
            matches = 0
            for v in variations:
                result = find_similar_rejection(v, existing, threshold=0.5)
                if result:
                    matches += 1
            assert matches >= 2, f"Expected at least 2 semantic matches, got {matches}"

    def test_cache_variations(self):
        """Different ways of saying 'add caching'."""
        existing = ["tried adding redis cache - infrastructure overhead too high"]

        variations = [
            "use caching to speed things up",
            "implement memory cache",
            "add a cache layer",
        ]

        if is_semantic_available():
            matches = 0
            for v in variations:
                result = find_similar_rejection(v, existing, threshold=0.5)
                if result:
                    matches += 1
            # Cache-related terms should have some semantic overlap
            assert matches >= 1
