"""Tests for LanceDB graph store."""
import pytest
import tempfile
from pathlib import Path

from mind.v3.graph.store import GraphStore


@pytest.fixture
def temp_graph():
    """Create a temporary graph store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = GraphStore(Path(tmpdir) / "graph")
        yield store


class TestGraphStore:
    """Test GraphStore class."""

    def test_create_store(self, temp_graph):
        """Should create store with all tables."""
        assert temp_graph.is_initialized()
        tables = temp_graph.list_tables()
        assert "decisions" in tables
        assert "entities" in tables
        assert "patterns" in tables

    def test_add_decision(self, temp_graph):
        """Should add decision to graph."""
        decision = {
            "action": "Used SQLite for storage",
            "reasoning": "Need portability",
            "confidence": 0.85,
        }

        doc_id = temp_graph.add_decision(decision)

        assert doc_id is not None
        assert doc_id.startswith("dec_")

        retrieved = temp_graph.get_decision(doc_id)
        assert retrieved is not None
        assert retrieved["action"] == "Used SQLite for storage"
        assert retrieved["reasoning"] == "Need portability"

    def test_add_decision_with_alternatives(self, temp_graph):
        """Should store decision alternatives."""
        decision = {
            "action": "Chose React over Vue",
            "reasoning": "Better ecosystem",
            "alternatives": ["Vue", "Angular", "Svelte"],
            "confidence": 0.9,
        }

        doc_id = temp_graph.add_decision(decision)
        retrieved = temp_graph.get_decision(doc_id)

        assert retrieved["alternatives"] == ["Vue", "Angular", "Svelte"]

    def test_search_decisions_by_text(self, temp_graph):
        """Should search decisions by text similarity."""
        temp_graph.add_decision({
            "action": "Used SQLite for storage",
            "reasoning": "Need portability and simplicity",
        })
        temp_graph.add_decision({
            "action": "Used PostgreSQL for production",
            "reasoning": "Need scalability and reliability",
        })
        temp_graph.add_decision({
            "action": "Chose functional programming style",
            "reasoning": "Better testability",
        })

        results = temp_graph.search_decisions("portable database storage", limit=5)

        assert len(results) >= 1
        # SQLite decision should rank higher for "portable storage"
        assert any("SQLite" in r["action"] for r in results[:2])

    def test_add_entity(self, temp_graph):
        """Should add entity to graph."""
        entity = {
            "name": "storage.py",
            "type": "file",
            "description": "Handles database storage operations",
        }

        doc_id = temp_graph.add_entity(entity)

        assert doc_id is not None
        assert doc_id.startswith("ent_")

    def test_get_entity(self, temp_graph):
        """Should retrieve entity by ID."""
        entity = {
            "name": "UserService",
            "type": "class",
            "description": "Manages user operations",
        }

        doc_id = temp_graph.add_entity(entity)
        retrieved = temp_graph.get_entity(doc_id)

        assert retrieved is not None
        assert retrieved["name"] == "UserService"
        assert retrieved["type"] == "class"

    def test_search_entities(self, temp_graph):
        """Should search entities by text."""
        temp_graph.add_entity({
            "name": "storage.py",
            "type": "file",
            "description": "Database storage module",
        })
        temp_graph.add_entity({
            "name": "auth.py",
            "type": "file",
            "description": "Authentication and authorization",
        })

        results = temp_graph.search_entities("database", limit=5)

        assert len(results) >= 1
        assert any("storage" in r["name"] for r in results)

    def test_add_pattern(self, temp_graph):
        """Should add pattern to graph."""
        pattern = {
            "description": "Prefers functional programming style over OOP",
            "pattern_type": "preference",
            "confidence": 0.8,
            "evidence_count": 5,
        }

        doc_id = temp_graph.add_pattern(pattern)

        assert doc_id is not None
        assert doc_id.startswith("pat_")

    def test_get_pattern(self, temp_graph):
        """Should retrieve pattern by ID."""
        pattern = {
            "description": "Always writes tests before implementation",
            "pattern_type": "habit",
            "confidence": 0.95,
            "evidence_count": 20,
        }

        doc_id = temp_graph.add_pattern(pattern)
        retrieved = temp_graph.get_pattern(doc_id)

        assert retrieved is not None
        assert "tests before" in retrieved["description"]
        assert abs(retrieved["confidence"] - 0.95) < 0.001  # Float precision

    def test_search_patterns(self, temp_graph):
        """Should search patterns by text."""
        temp_graph.add_pattern({
            "description": "Prefers functional style",
            "pattern_type": "preference",
            "confidence": 0.8,
        })
        temp_graph.add_pattern({
            "description": "Always uses TypeScript",
            "pattern_type": "habit",
            "confidence": 0.9,
        })

        results = temp_graph.search_patterns("functional programming", limit=5)

        assert len(results) >= 1

    def test_update_pattern_confidence(self, temp_graph):
        """Should update pattern confidence."""
        doc_id = temp_graph.add_pattern({
            "description": "Prefers short functions",
            "pattern_type": "preference",
            "confidence": 0.5,
            "evidence_count": 2,
        })

        temp_graph.update_pattern(doc_id, confidence=0.8, evidence_count=10)

        retrieved = temp_graph.get_pattern(doc_id)
        assert abs(retrieved["confidence"] - 0.8) < 0.001  # Float precision
        assert retrieved["evidence_count"] == 10

    def test_count_nodes(self, temp_graph):
        """Should count nodes by type."""
        temp_graph.add_decision({"action": "Decision 1"})
        temp_graph.add_decision({"action": "Decision 2"})
        temp_graph.add_entity({"name": "Entity 1", "type": "file"})
        temp_graph.add_pattern({"description": "Pattern 1"})

        counts = temp_graph.get_counts()

        assert counts["decisions"] == 2
        assert counts["entities"] == 1
        assert counts["patterns"] == 1
