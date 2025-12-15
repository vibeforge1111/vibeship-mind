"""Tests for semantic similarity loop detection."""

import pytest
from mind.similarity import semantic_similarity, find_similar_rejection


class TestSemanticSimilarity:
    """Tests for semantic similarity."""

    def test_identical_texts(self):
        sim = semantic_similarity("increase the timeout", "increase the timeout")
        assert sim > 0.99

    def test_semantically_similar(self):
        """These are semantically similar but have different words."""
        sim = semantic_similarity(
            "increase the timeout",
            "extend the wait duration"
        )
        assert sim > 0.3  # Should have some similarity

    def test_semantically_different(self):
        sim = semantic_similarity(
            "increase the timeout",
            "refactor the database schema"
        )
        assert sim < 0.3


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
        ]
        result = find_similar_rejection(
            "bump the timeout value",
            rejections,
            threshold=0.5
        )
        assert result is not None

    def test_below_threshold(self):
        """Test that dissimilar rejections don't trigger warning."""
        rejections = [
            "tried using mongodb - overkill for this",
        ]
        result = find_similar_rejection(
            "increase timeout",
            rejections,
            threshold=0.6
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
        assert result is not None
        assert "timeout" in result["similar_to"].lower()


class TestRealWorldScenarios:
    """Test scenarios from actual usage patterns."""

    def test_timeout_variations(self):
        """Different ways of saying 'increase timeout'."""
        existing = ["tried increasing timeout to 60s - still failing"]

        # These should match
        should_match = [
            "bump the timeout again",
            "increase the timeout more",
            "try a longer timeout",
        ]

        for phrase in should_match:
            result = find_similar_rejection(phrase, existing, threshold=0.5)
            assert result is not None, f"'{phrase}' should match"

    def test_unrelated_not_matched(self):
        """Unrelated topics should not match."""
        existing = ["tried increasing timeout to 60s - still failing"]

        should_not_match = [
            "use redis for caching",
            "refactor the database",
            "add unit tests",
        ]

        for phrase in should_not_match:
            result = find_similar_rejection(phrase, existing, threshold=0.5)
            assert result is None, f"'{phrase}' should NOT match"
