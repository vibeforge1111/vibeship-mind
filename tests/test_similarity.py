"""Tests for semantic similarity loop detection and search."""

import pytest
from mind.similarity import (
    semantic_similarity,
    find_similar_rejection,
    semantic_search,
    semantic_search_strings,
)


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


class TestSemanticSearch:
    """Tests for semantic search over items."""

    def test_empty_query(self):
        items = [{"content": "hello world"}]
        result = semantic_search("", items)
        assert result == []

    def test_empty_items(self):
        result = semantic_search("hello", [])
        assert result == []

    def test_finds_relevant_item(self):
        items = [
            {"content": "Windows needs ctypes for process detection", "id": 1},
            {"content": "Use Click for CLI because it's simple", "id": 2},
            {"content": "Python encoding issues on Windows", "id": 3},
        ]
        results = semantic_search("Windows process", items, threshold=0.3)
        assert len(results) > 0
        # First result should be about Windows process detection
        assert "ctypes" in results[0]["content"] or "Windows" in results[0]["content"]

    def test_semantic_not_keyword(self):
        """Test that it finds semantically similar, not just keyword matches."""
        items = [
            {"content": "increase the wait duration", "id": 1},
            {"content": "add more vegetables to diet", "id": 2},
        ]
        results = semantic_search("extend the timeout", items, threshold=0.3)
        assert len(results) > 0
        # Should match "wait duration" not "vegetables"
        assert "wait" in results[0]["content"]

    def test_respects_threshold(self):
        items = [
            {"content": "completely unrelated topic about cooking recipes", "id": 1},
        ]
        results = semantic_search("Python async programming", items, threshold=0.5)
        assert len(results) == 0

    def test_respects_limit(self):
        items = [
            {"content": f"Python topic number {i}", "id": i}
            for i in range(20)
        ]
        results = semantic_search("Python programming", items, threshold=0.2, limit=5)
        assert len(results) <= 5

    def test_returns_similarity_as_relevance(self):
        items = [{"content": "async await programming patterns", "id": 1}]
        results = semantic_search("async programming", items, threshold=0.3)
        assert len(results) > 0
        assert "relevance" not in results[0]  # We rename it
        assert "semantic_similarity" in results[0]

    def test_custom_content_key(self):
        items = [
            {"text": "Windows process detection", "id": 1},
            {"text": "Linux file permissions", "id": 2},
        ]
        results = semantic_search("Windows", items, content_key="text", threshold=0.3)
        assert len(results) > 0


class TestSemanticSearchStrings:
    """Tests for semantic search over plain strings."""

    def test_empty_query(self):
        result = semantic_search_strings("", ["hello"])
        assert result == []

    def test_empty_strings(self):
        result = semantic_search_strings("hello", [])
        assert result == []

    def test_finds_relevant_string(self):
        strings = [
            "Windows needs ctypes for process detection",
            "Use Click for CLI because it's simple",
            "Python encoding issues on Windows",
        ]
        results = semantic_search_strings("Windows process", strings, threshold=0.3)
        assert len(results) > 0
        assert "Windows" in results[0]["content"]

    def test_returns_line_index(self):
        strings = [
            "First line",
            "Second line about Python",
            "Third line",
        ]
        results = semantic_search_strings("Python programming", strings, threshold=0.2)
        assert len(results) > 0
        # Should return the index of the matched line
        assert "line_index" in results[0]
        assert results[0]["line_index"] == 1  # Second line (0-indexed)

    def test_skips_empty_strings(self):
        strings = ["", "  ", "actual content here"]
        results = semantic_search_strings("content", strings, threshold=0.2)
        # Should only match the actual content, not empty strings
        for r in results:
            assert r["content"].strip() != ""

    def test_respects_limit(self):
        strings = [f"Python topic {i}" for i in range(20)]
        results = semantic_search_strings("Python", strings, threshold=0.2, limit=3)
        assert len(results) <= 3
