"""Tests for context injection hook."""
import pytest

from mind.v3.retrieval.context_injection import (
    ContextInjector,
    ContextInjectorConfig,
    InjectedContext,
)
from mind.v3.retrieval.search import HybridSearch, SearchResult


class TestContextInjectorConfig:
    """Test ContextInjectorConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = ContextInjectorConfig()

        assert config.max_context_items == 5
        assert config.max_context_length == 2000
        assert config.min_relevance_score == 0.0  # RRF scores are very small

    def test_custom_config(self):
        """Should accept custom settings."""
        config = ContextInjectorConfig(
            max_context_items=10,
            max_context_length=4000,
            min_relevance_score=0.3,
        )

        assert config.max_context_items == 10
        assert config.max_context_length == 4000


class TestInjectedContext:
    """Test InjectedContext dataclass."""

    def test_create_injected_context(self):
        """Should create injected context."""
        context = InjectedContext(
            items=[
                {"id": "doc1", "text": "Hello", "score": 0.9}
            ],
            total_items=1,
            truncated=False,
        )

        assert len(context.items) == 1
        assert context.truncated is False

    def test_to_markdown(self):
        """Should format as markdown."""
        context = InjectedContext(
            items=[
                {"id": "decision-1", "text": "Use Python for scripting", "score": 0.9, "type": "decision"},
                {"id": "learning-1", "text": "SQLite is fast enough", "score": 0.8, "type": "learning"},
            ],
            total_items=2,
            truncated=False,
        )

        md = context.to_markdown()

        assert "# Relevant Context" in md
        assert "Use Python for scripting" in md
        assert "SQLite is fast enough" in md

    def test_to_markdown_empty(self):
        """Should return empty string for no items."""
        context = InjectedContext(items=[], total_items=0, truncated=False)

        assert context.to_markdown() == ""


class TestContextInjector:
    """Test ContextInjector."""

    @pytest.fixture
    def search_engine(self):
        """Create search engine with sample documents."""
        search = HybridSearch()
        search.add_documents([
            {
                "id": "decision-1",
                "text": "Decided to use Python for all scripting tasks",
                "metadata": {"type": "decision"},
            },
            {
                "id": "decision-2",
                "text": "Chose PostgreSQL over MySQL for the database",
                "metadata": {"type": "decision"},
            },
            {
                "id": "learning-1",
                "text": "SQLite is fast enough for local development",
                "metadata": {"type": "learning"},
            },
            {
                "id": "problem-1",
                "text": "API rate limiting causes issues with bulk operations",
                "metadata": {"type": "problem"},
            },
        ])
        return search

    @pytest.fixture
    def injector(self, search_engine):
        """Create context injector."""
        return ContextInjector(search=search_engine)

    def test_create_injector(self, injector):
        """Should create context injector."""
        assert injector is not None

    def test_inject_finds_relevant_context(self, injector):
        """Should find relevant context for query."""
        result = injector.inject("What database should I use?")

        assert result.total_items >= 1
        # Should find database-related items
        texts = [item["text"] for item in result.items]
        assert any("database" in t.lower() or "PostgreSQL" in t or "SQLite" in t for t in texts)

    def test_inject_respects_max_items(self, search_engine):
        """Should respect max_context_items limit."""
        config = ContextInjectorConfig(max_context_items=2)
        injector = ContextInjector(search=search_engine, config=config)

        result = injector.inject("programming")

        assert len(result.items) <= 2

    def test_inject_filters_low_scores(self, search_engine):
        """Should filter results below min_relevance_score."""
        config = ContextInjectorConfig(min_relevance_score=0.5)
        injector = ContextInjector(search=search_engine, config=config)

        result = injector.inject("quantum physics")  # Unrelated query

        # All items should have score >= min_relevance_score
        for item in result.items:
            assert item["score"] >= 0.5

    def test_inject_includes_metadata(self, injector):
        """Should include metadata in results."""
        result = injector.inject("Python scripting")

        # Find the Python decision
        python_items = [item for item in result.items if "Python" in item.get("text", "")]
        if python_items:
            assert "type" in python_items[0]

    def test_inject_empty_query(self, injector):
        """Should handle empty query."""
        result = injector.inject("")

        # Should return empty or default results
        assert isinstance(result, InjectedContext)

    def test_inject_truncates_long_context(self, search_engine):
        """Should truncate if context exceeds max_length."""
        config = ContextInjectorConfig(max_context_length=50)  # Very short
        injector = ContextInjector(search=search_engine, config=config)

        result = injector.inject("database")

        assert result.truncated is True


class TestContextInjectorWithReranking:
    """Test context injection with reranking enabled."""

    @pytest.fixture
    def search_engine(self):
        """Create search engine with sample documents."""
        search = HybridSearch()
        search.add_documents([
            {"id": "doc1", "text": "Python is great for data science"},
            {"id": "doc2", "text": "JavaScript runs in browsers"},
            {"id": "doc3", "text": "Python excels at machine learning"},
        ])
        return search

    def test_injector_with_reranking(self, search_engine):
        """Should use reranker when enabled."""
        config = ContextInjectorConfig(use_reranking=True)
        injector = ContextInjector(search=search_engine, config=config)

        result = injector.inject("machine learning with Python")

        # Should find Python/ML related items
        assert result.total_items >= 1
        texts = [item["text"] for item in result.items]
        assert any("Python" in t for t in texts)


class TestContextInjectorFormatting:
    """Test context formatting options."""

    @pytest.fixture
    def search_engine(self):
        """Create search engine."""
        search = HybridSearch()
        search.add_documents([
            {
                "id": "decision-1",
                "text": "Use TypeScript for type safety",
                "metadata": {"type": "decision", "date": "2025-12-25"},
            },
        ])
        return search

    def test_format_with_scores(self, search_engine):
        """Should include scores when configured."""
        config = ContextInjectorConfig(include_scores=True)
        injector = ContextInjector(search=search_engine, config=config)

        result = injector.inject("TypeScript")
        md = result.to_markdown()

        # Should have score in output
        assert "score" in md.lower() or "relevance" in md.lower() or "%" in md

    def test_format_grouped_by_type(self, search_engine):
        """Should group by type when configured."""
        # Add more documents with different types
        search_engine.add_documents([
            {"id": "learning-1", "text": "React hooks are powerful", "metadata": {"type": "learning"}},
        ])

        config = ContextInjectorConfig(group_by_type=True)
        injector = ContextInjector(search=search_engine, config=config)

        result = injector.inject("TypeScript React")
        md = result.to_markdown()

        # Should have type headers
        assert "Decision" in md or "Learning" in md
