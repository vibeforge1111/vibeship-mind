"""Tests for QueryExpander."""
import pytest

from mind.v3.retrieval.query_expander import QueryExpander, ExpanderConfig, ExpandedQuery


class TestExpanderConfig:
    """Tests for ExpanderConfig."""

    def test_default_config(self):
        config = ExpanderConfig()
        assert config.enabled is True
        assert config.include_synonyms is True
        assert config.extract_entities is True

    def test_custom_config(self):
        config = ExpanderConfig(enabled=False, max_expansions=5)
        assert config.enabled is False
        assert config.max_expansions == 5


class TestExpandedQuery:
    """Tests for ExpandedQuery."""

    def test_get_search_queries(self):
        eq = ExpandedQuery(
            original="fix the bug",
            sub_queries=["fix the issue", "repair the problem"],
        )
        queries = eq.get_search_queries()
        assert "fix the bug" in queries
        assert len(queries) <= 4

    def test_get_keywords(self):
        eq = ExpandedQuery(
            original="fix error",
            expanded_terms=["bug", "issue"],
            entities=["UserService"],
        )
        keywords = eq.get_keywords()
        assert "fix" in keywords
        assert "bug" in keywords
        assert "userservice" in keywords


class TestQueryExpander:
    """Tests for QueryExpander."""

    def test_create_expander(self):
        expander = QueryExpander()
        assert expander is not None

    def test_expand_simple_query(self):
        expander = QueryExpander()
        result = expander.expand("fix the error")

        assert result.original == "fix the error"
        assert len(result.expanded_terms) > 0  # Should have synonyms

    def test_expand_with_synonyms(self):
        expander = QueryExpander()
        result = expander.expand("fix the bug")

        # Should find synonyms for 'fix' and 'bug'
        all_terms = set(result.expanded_terms)
        assert any(t in all_terms for t in ["resolve", "patch", "error", "issue"])

    def test_extract_entities(self):
        expander = QueryExpander()
        result = expander.expand("modify the UserService class")

        assert "UserService" in result.entities

    def test_extract_file_entities(self):
        expander = QueryExpander()
        result = expander.expand("check the auth.py file")

        assert "auth.py" in result.entities

    def test_generate_sub_queries(self):
        expander = QueryExpander()
        result = expander.expand("fix the login bug and update the tests")

        assert len(result.sub_queries) > 0

    def test_disabled_expander(self):
        config = ExpanderConfig(enabled=False)
        expander = QueryExpander(config=config)
        result = expander.expand("fix error")

        assert result.original == "fix error"
        assert len(result.expanded_terms) == 0
        assert len(result.entities) == 0

    def test_no_synonyms_config(self):
        config = ExpanderConfig(include_synonyms=False)
        expander = QueryExpander(config=config)
        result = expander.expand("fix the error")

        assert len(result.expanded_terms) == 0

    def test_no_entities_config(self):
        config = ExpanderConfig(extract_entities=False)
        expander = QueryExpander(config=config)
        result = expander.expand("modify UserService")

        assert len(result.entities) == 0
