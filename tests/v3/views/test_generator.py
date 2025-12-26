"""Tests for view generator."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from mind.v3.views.generator import ViewGenerator


@pytest.fixture
def mock_graph_store():
    """Create a mock GraphStore."""
    store = MagicMock()
    store.get_all_decisions.return_value = []
    store.get_all_patterns.return_value = []
    store.search_policies.return_value = []
    return store


@pytest.fixture
def output_dir(tmp_path):
    """Create temp output directory."""
    return tmp_path / "views"


class TestViewGenerator:
    """Test ViewGenerator class."""

    def test_create_generator(self, mock_graph_store, output_dir):
        """Should create generator with store and output dir."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        assert gen.graph is mock_graph_store
        assert gen.output_dir == output_dir

    def test_output_dir_created(self, mock_graph_store, output_dir):
        """Should create output directory if it doesn't exist."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        assert not output_dir.exists()
        gen.generate_decisions_view()
        assert output_dir.exists()


class TestDecisionsView:
    """Test decisions view generation."""

    def test_generate_empty_decisions(self, mock_graph_store, output_dir):
        """Should generate file with no decisions message."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_decisions_view()

        assert path.exists()
        content = path.read_text()
        assert "# Decisions" in content
        assert "No decisions recorded yet" in content

    def test_generate_with_decisions(self, mock_graph_store, output_dir):
        """Should generate file with decision entries."""
        mock_graph_store.get_all_decisions.return_value = [
            {
                "action": "Use SQLite",
                "reasoning": "Simpler than PostgreSQL",
                "confidence": 0.85,
                "alternatives": ["PostgreSQL", "MySQL"],
            },
            {
                "action": "Use pytest",
                "reasoning": "Standard Python testing",
                "confidence": 0.9,
            },
        ]
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_decisions_view()

        content = path.read_text()
        assert "## Use SQLite" in content
        assert "Simpler than PostgreSQL" in content
        assert "85%" in content
        assert "PostgreSQL" in content
        assert "## Use pytest" in content

    def test_decisions_file_name(self, mock_graph_store, output_dir):
        """Should write to DECISIONS.md."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_decisions_view()

        assert path.name == "DECISIONS.md"


class TestPatternsView:
    """Test patterns view generation."""

    def test_generate_empty_patterns(self, mock_graph_store, output_dir):
        """Should generate file with no patterns message."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_patterns_view()

        assert path.exists()
        content = path.read_text()
        assert "# Patterns" in content
        assert "No patterns detected yet" in content

    def test_generate_with_patterns(self, mock_graph_store, output_dir):
        """Should generate file with pattern entries."""
        mock_graph_store.get_all_patterns.return_value = [
            {
                "description": "Always use type hints",
                "pattern_type": "preference",
                "confidence": 0.8,
                "evidence_count": 5,
            },
            {
                "description": "Avoid global variables",
                "pattern_type": "avoidance",
                "confidence": 0.9,
                "evidence_count": 3,
            },
        ]
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_patterns_view()

        content = path.read_text()
        assert "## Preference Patterns" in content
        assert "Always use type hints" in content
        assert "80%" in content
        assert "## Avoidance Patterns" in content
        assert "Avoid global variables" in content

    def test_patterns_grouped_by_type(self, mock_graph_store, output_dir):
        """Should group patterns by type."""
        mock_graph_store.get_all_patterns.return_value = [
            {"description": "Pattern A", "pattern_type": "habit", "confidence": 0.7, "evidence_count": 2},
            {"description": "Pattern B", "pattern_type": "preference", "confidence": 0.6, "evidence_count": 1},
            {"description": "Pattern C", "pattern_type": "habit", "confidence": 0.8, "evidence_count": 4},
        ]
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_patterns_view()

        content = path.read_text()
        # Should have both sections
        assert "## Habit Patterns" in content
        assert "## Preference Patterns" in content


class TestPoliciesView:
    """Test policies view generation."""

    def test_generate_empty_policies(self, mock_graph_store, output_dir):
        """Should generate file with no policies message."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_policies_view()

        assert path.exists()
        content = path.read_text()
        assert "# Policies" in content
        assert "No policies defined yet" in content

    def test_generate_with_active_policies(self, mock_graph_store, output_dir):
        """Should generate file with active policy entries."""
        mock_graph_store.search_policies.return_value = [
            {
                "rule": "Always run tests before commit",
                "scope": "project",
                "source": "explicit",
                "active": True,
            },
        ]
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_policies_view()

        content = path.read_text()
        assert "## Active Policies" in content
        assert "Always run tests before commit" in content
        assert "**Scope:** project" in content

    def test_generate_with_inactive_policies(self, mock_graph_store, output_dir):
        """Should show inactive policies with strikethrough."""
        mock_graph_store.search_policies.return_value = [
            {
                "rule": "Old rule no longer used",
                "scope": "global",
                "source": "inferred",
                "active": False,
            },
        ]
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_policies_view()

        content = path.read_text()
        assert "## Inactive Policies" in content
        assert "~~Old rule no longer used~~" in content

    def test_separates_active_and_inactive(self, mock_graph_store, output_dir):
        """Should separate active and inactive policies."""
        mock_graph_store.search_policies.return_value = [
            {"rule": "Active rule", "scope": "project", "source": "explicit", "active": True},
            {"rule": "Inactive rule", "scope": "project", "source": "inferred", "active": False},
        ]
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_policies_view()

        content = path.read_text()
        assert "## Active Policies" in content
        assert "## Inactive Policies" in content


class TestGenerateAll:
    """Test generate_all method."""

    def test_generates_all_views(self, mock_graph_store, output_dir):
        """Should generate all three views."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        paths = gen.generate_all()

        assert len(paths) == 3
        assert all(p.exists() for p in paths)

        names = [p.name for p in paths]
        assert "DECISIONS.md" in names
        assert "PATTERNS.md" in names
        assert "POLICIES.md" in names

    def test_returns_correct_paths(self, mock_graph_store, output_dir):
        """Should return paths to generated files."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        paths = gen.generate_all()

        for path in paths:
            assert path.parent == output_dir


class TestViewContent:
    """Test view content formatting."""

    def test_includes_timestamp(self, mock_graph_store, output_dir):
        """Should include generation timestamp."""
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_decisions_view()

        content = path.read_text()
        assert "*Generated:" in content

    def test_utf8_encoding(self, mock_graph_store, output_dir):
        """Should handle unicode characters."""
        mock_graph_store.get_all_decisions.return_value = [
            {
                "action": "Use em-dash \u2014 for readability",
                "reasoning": "Better typography \u2713",
                "confidence": 0.7,
            },
        ]
        gen = ViewGenerator(mock_graph_store, output_dir)

        path = gen.generate_decisions_view()

        content = path.read_text(encoding="utf-8")
        assert "\u2014" in content
        assert "\u2713" in content
