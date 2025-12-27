"""Tests for reranking."""
import pytest

from mind.v3.retrieval.reranker import (
    Reranker,
    RerankerConfig,
    SimpleReranker,
)
from mind.v3.retrieval.search import SearchResult


class TestRerankerConfig:
    """Test RerankerConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = RerankerConfig()

        assert config.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert config.top_k == 10
        assert config.use_gpu is False

    def test_custom_config(self):
        """Should accept custom settings."""
        config = RerankerConfig(
            model_name="custom-model",
            top_k=5,
            use_gpu=True,
        )

        assert config.model_name == "custom-model"
        assert config.top_k == 5


class TestSimpleReranker:
    """Test SimpleReranker (fallback without ML)."""

    def test_create_reranker(self):
        """Should create simple reranker."""
        reranker = SimpleReranker()

        assert reranker is not None

    def test_rerank_by_keyword_overlap(self):
        """Should rerank based on query-result overlap."""
        reranker = SimpleReranker()

        results = [
            SearchResult(id="doc1", content={"text": "Python programming language"}, score=0.5),
            SearchResult(id="doc2", content={"text": "Python is great for data science"}, score=0.6),
            SearchResult(id="doc3", content={"text": "JavaScript runs in browsers"}, score=0.7),
        ]

        reranked = reranker.rerank(
            query="Python programming",
            results=results,
            top_k=3,
        )

        # Python docs should be ranked higher after reranking
        assert len(reranked) == 3
        texts = [r.content.get("text", "") for r in reranked[:2]]
        assert all("Python" in t for t in texts)

    def test_rerank_respects_top_k(self):
        """Should respect top_k limit."""
        reranker = SimpleReranker()

        results = [
            SearchResult(id="doc1", content={"text": "First"}, score=0.5),
            SearchResult(id="doc2", content={"text": "Second"}, score=0.6),
            SearchResult(id="doc3", content={"text": "Third"}, score=0.7),
        ]

        reranked = reranker.rerank(
            query="test",
            results=results,
            top_k=2,
        )

        assert len(reranked) == 2

    def test_rerank_empty_results(self):
        """Should handle empty results."""
        reranker = SimpleReranker()

        reranked = reranker.rerank(
            query="test",
            results=[],
            top_k=5,
        )

        assert reranked == []

    def test_rerank_preserves_metadata(self):
        """Should preserve result metadata."""
        reranker = SimpleReranker()

        results = [
            SearchResult(
                id="doc1",
                content={"text": "Python"},
                score=0.5,
                metadata={"source": "decisions"},
            ),
        ]

        reranked = reranker.rerank(
            query="Python",
            results=results,
            top_k=1,
        )

        assert reranked[0].metadata["source"] == "decisions"

    def test_rerank_updates_scores(self):
        """Should update scores after reranking."""
        reranker = SimpleReranker()

        results = [
            SearchResult(id="doc1", content={"text": "Python programming"}, score=0.3),
            SearchResult(id="doc2", content={"text": "Java programming"}, score=0.8),
        ]

        reranked = reranker.rerank(
            query="Python",
            results=results,
            top_k=2,
        )

        # Python doc should have higher score after reranking
        python_result = next(r for r in reranked if "Python" in r.content["text"])
        java_result = next(r for r in reranked if "Java" in r.content["text"])

        assert python_result.score > java_result.score


class TestReranker:
    """Test Reranker with fallback."""

    def test_create_reranker(self):
        """Should create reranker."""
        reranker = Reranker()

        assert reranker is not None

    def test_reranker_with_fallback(self):
        """Should work with fallback when model unavailable."""
        config = RerankerConfig(
            model_name="nonexistent-model",
            fallback_to_simple=True,
        )
        reranker = Reranker(config=config)

        results = [
            SearchResult(id="doc1", content={"text": "Python"}, score=0.5),
        ]

        reranked = reranker.rerank(
            query="Python",
            results=results,
            top_k=1,
        )

        assert len(reranked) == 1

    def test_is_using_fallback(self):
        """Should report when using fallback."""
        config = RerankerConfig(
            model_name="nonexistent-model",
            fallback_to_simple=True,
        )
        reranker = Reranker(config=config)

        assert reranker.is_fallback is True

    def test_rerank_integration(self):
        """Should rerank search results effectively."""
        reranker = Reranker()

        results = [
            SearchResult(id="doc1", content={"text": "Database storage with SQLite"}, score=0.5),
            SearchResult(id="doc2", content={"text": "SQLite is a great portable database"}, score=0.4),
            SearchResult(id="doc3", content={"text": "Redis provides caching"}, score=0.6),
        ]

        reranked = reranker.rerank(
            query="SQLite database",
            results=results,
            top_k=3,
        )

        # SQLite docs should rank higher
        assert len(reranked) == 3
        top_texts = [r.content.get("text", "") for r in reranked[:2]]
        assert all("SQLite" in t for t in top_texts)
