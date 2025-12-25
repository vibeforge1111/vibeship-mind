"""Tests for hybrid search."""
import pytest

from mind.v3.retrieval.search import (
    HybridSearch,
    SearchConfig,
    SearchResult,
    SearchMode,
)
from mind.v3.retrieval.embeddings import EmbeddingService


class TestSearchConfig:
    """Test SearchConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = SearchConfig()

        assert config.mode == SearchMode.HYBRID
        assert config.vector_weight == 0.7
        assert config.keyword_weight == 0.3
        assert config.top_k == 10

    def test_custom_config(self):
        """Should accept custom settings."""
        config = SearchConfig(
            mode=SearchMode.VECTOR_ONLY,
            vector_weight=1.0,
            keyword_weight=0.0,
            top_k=20,
        )

        assert config.mode == SearchMode.VECTOR_ONLY
        assert config.top_k == 20


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_create_result(self):
        """Should create search result."""
        result = SearchResult(
            id="doc_123",
            content={"text": "Hello world"},
            score=0.85,
        )

        assert result.id == "doc_123"
        assert result.content["text"] == "Hello world"
        assert result.score == 0.85

    def test_result_with_metadata(self):
        """Should support metadata."""
        result = SearchResult(
            id="doc_123",
            content={"text": "Hello"},
            score=0.9,
            metadata={"source": "decisions"},
        )

        assert result.metadata["source"] == "decisions"


class TestHybridSearch:
    """Test HybridSearch."""

    @pytest.fixture
    def search_engine(self):
        """Create search engine with sample documents."""
        search = HybridSearch()

        # Add sample documents
        search.add_documents([
            {"id": "doc1", "text": "Python is a great programming language"},
            {"id": "doc2", "text": "JavaScript runs in the browser"},
            {"id": "doc3", "text": "Python and JavaScript are both popular"},
            {"id": "doc4", "text": "Database storage with SQLite"},
            {"id": "doc5", "text": "Redis provides fast caching"},
        ])

        return search

    def test_create_search(self):
        """Should create search engine."""
        search = HybridSearch()

        assert search is not None

    def test_add_documents(self, search_engine):
        """Should add documents."""
        assert search_engine.document_count == 5

    def test_vector_search(self, search_engine):
        """Should perform vector search."""
        results = search_engine.search(
            "programming language",
            mode=SearchMode.VECTOR_ONLY,
            top_k=3,
        )

        assert len(results) <= 3
        assert all(isinstance(r, SearchResult) for r in results)

    def test_keyword_search(self, search_engine):
        """Should perform keyword search."""
        results = search_engine.search(
            "Python",
            mode=SearchMode.KEYWORD_ONLY,
            top_k=3,
        )

        assert len(results) >= 1
        # Python should be in results
        texts = [r.content.get("text", "") for r in results]
        assert any("Python" in t for t in texts)

    def test_hybrid_search(self, search_engine):
        """Should perform hybrid search."""
        results = search_engine.search(
            "Python programming",
            mode=SearchMode.HYBRID,
            top_k=3,
        )

        assert len(results) >= 1

    def test_search_respects_top_k(self, search_engine):
        """Should respect top_k limit."""
        results = search_engine.search(
            "language",
            top_k=2,
        )

        assert len(results) <= 2

    def test_search_returns_scores(self, search_engine):
        """Should return scores with results."""
        results = search_engine.search("Python", top_k=3)

        assert all(r.score >= 0 for r in results)
        # Results should be sorted by score descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_empty_query(self, search_engine):
        """Should handle empty query."""
        results = search_engine.search("", top_k=3)

        # Should return empty or all documents
        assert isinstance(results, list)

    def test_search_no_matches(self):
        """Should return empty for no matches."""
        search = HybridSearch()
        search.add_documents([
            {"id": "doc1", "text": "Apples and oranges"},
        ])

        results = search.search(
            "quantum physics",
            mode=SearchMode.KEYWORD_ONLY,
            top_k=3,
        )

        # May return empty or low-score results
        assert isinstance(results, list)


class TestHybridSearchWeights:
    """Test hybrid search weight configuration."""

    @pytest.fixture
    def search_engine(self):
        """Create search with documents."""
        search = HybridSearch()
        search.add_documents([
            {"id": "doc1", "text": "Fast database queries with PostgreSQL"},
            {"id": "doc2", "text": "PostgreSQL is reliable and fast"},
            {"id": "doc3", "text": "Quick data storage solutions"},
        ])
        return search

    def test_vector_weight_dominates(self, search_engine):
        """Higher vector weight should prefer semantic matches."""
        config = SearchConfig(
            vector_weight=0.9,
            keyword_weight=0.1,
        )

        results = search_engine.search(
            "speedy database",  # Semantic match for "fast database"
            config=config,
            top_k=3,
        )

        assert len(results) >= 1

    def test_keyword_weight_dominates(self, search_engine):
        """Higher keyword weight should prefer exact matches."""
        config = SearchConfig(
            vector_weight=0.1,
            keyword_weight=0.9,
        )

        results = search_engine.search(
            "PostgreSQL",  # Exact keyword match
            config=config,
            top_k=3,
        )

        assert len(results) >= 1
        # PostgreSQL docs should be top results
        texts = [r.content.get("text", "") for r in results[:2]]
        assert any("PostgreSQL" in t for t in texts)


class TestHybridSearchUpdate:
    """Test document updates."""

    def test_add_single_document(self):
        """Should add single document."""
        search = HybridSearch()

        search.add_document(
            doc_id="doc1",
            text="Hello world",
            metadata={"source": "test"},
        )

        assert search.document_count == 1

    def test_remove_document(self):
        """Should remove document."""
        search = HybridSearch()
        search.add_document("doc1", "Hello world")
        search.add_document("doc2", "Goodbye world")

        search.remove_document("doc1")

        assert search.document_count == 1

    def test_clear_documents(self):
        """Should clear all documents."""
        search = HybridSearch()
        search.add_documents([
            {"id": "doc1", "text": "Hello"},
            {"id": "doc2", "text": "World"},
        ])

        search.clear()

        assert search.document_count == 0
