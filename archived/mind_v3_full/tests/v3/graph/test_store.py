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


class TestPoliciesTable:
    """Test policies table operations."""

    def test_add_policy(self, temp_graph):
        """Should add policy to graph."""
        policy = {
            "rule": "Always use type hints in Python",
            "scope": "project",
            "source": "CLAUDE.md",
        }

        doc_id = temp_graph.add_policy(policy)

        assert doc_id is not None
        assert doc_id.startswith("pol_")

        retrieved = temp_graph.get_policy(doc_id)
        assert retrieved is not None
        assert retrieved["rule"] == "Always use type hints in Python"
        assert retrieved["scope"] == "project"
        assert retrieved["active"] is True

    def test_search_policies(self, temp_graph):
        """Should search policies by text."""
        temp_graph.add_policy({
            "rule": "Always use type hints in Python",
            "scope": "project",
        })
        temp_graph.add_policy({
            "rule": "Use SQLite for local storage",
            "scope": "project",
        })

        results = temp_graph.search_policies("type hints", limit=5)

        assert len(results) >= 1
        assert any("type hints" in r["rule"] for r in results)

    def test_deactivate_policy(self, temp_graph):
        """Should deactivate a policy."""
        doc_id = temp_graph.add_policy({
            "rule": "Old rule to remove",
            "scope": "project",
        })

        assert temp_graph.deactivate_policy(doc_id) is True

        retrieved = temp_graph.get_policy(doc_id)
        assert retrieved["active"] is False

    def test_search_policies_active_only(self, temp_graph):
        """Should filter inactive policies when searching."""
        active_id = temp_graph.add_policy({
            "rule": "Active policy about testing",
            "scope": "project",
        })
        inactive_id = temp_graph.add_policy({
            "rule": "Inactive policy about testing",
            "scope": "project",
        })
        temp_graph.deactivate_policy(inactive_id)

        results = temp_graph.search_policies("testing", limit=5, active_only=True)

        assert len(results) >= 1
        assert all(r["active"] is True for r in results)


class TestExceptionsTable:
    """Test exceptions table operations."""

    def test_add_exception(self, temp_graph):
        """Should add exception to graph."""
        # First add a policy
        policy_id = temp_graph.add_policy({
            "rule": "Always use type hints",
            "scope": "project",
        })

        exception = {
            "policy_id": policy_id,
            "condition": "In test files",
            "reason": "Type hints are less critical in tests",
        }

        doc_id = temp_graph.add_exception(exception)

        assert doc_id is not None
        assert doc_id.startswith("exc_")

        retrieved = temp_graph.get_exception(doc_id)
        assert retrieved is not None
        assert retrieved["policy_id"] == policy_id
        assert retrieved["condition"] == "In test files"

    def test_get_exceptions_for_policy(self, temp_graph):
        """Should get all exceptions for a policy."""
        policy_id = temp_graph.add_policy({
            "rule": "Always use type hints",
            "scope": "project",
        })

        temp_graph.add_exception({
            "policy_id": policy_id,
            "condition": "In test files",
            "reason": "Less critical in tests",
        })
        temp_graph.add_exception({
            "policy_id": policy_id,
            "condition": "In CLI scripts",
            "reason": "One-off scripts",
        })

        exceptions = temp_graph.get_exceptions_for_policy(policy_id)

        assert len(exceptions) == 2

    def test_search_exceptions(self, temp_graph):
        """Should search exceptions by text."""
        policy_id = temp_graph.add_policy({"rule": "Some policy"})
        temp_graph.add_exception({
            "policy_id": policy_id,
            "condition": "When performance is critical",
            "reason": "Optimization takes priority",
        })

        results = temp_graph.search_exceptions("performance", limit=5)

        assert len(results) >= 1


class TestPrecedentsTable:
    """Test precedents table operations."""

    def test_add_precedent(self, temp_graph):
        """Should add precedent to graph."""
        decision_id = temp_graph.add_decision({
            "action": "Chose SQLite over PostgreSQL",
            "reasoning": "Simpler deployment",
        })

        precedent = {
            "decision_id": decision_id,
            "context": "Local-first application",
            "outcome": "Worked well for single-user scenarios",
            "weight": 0.9,
        }

        doc_id = temp_graph.add_precedent(precedent)

        assert doc_id is not None
        assert doc_id.startswith("prc_")

        retrieved = temp_graph.get_precedent(doc_id)
        assert retrieved is not None
        assert retrieved["decision_id"] == decision_id
        assert abs(retrieved["weight"] - 0.9) < 0.001

    def test_get_precedents_for_decision(self, temp_graph):
        """Should get precedents for a decision."""
        decision_id = temp_graph.add_decision({
            "action": "Used functional style",
        })

        temp_graph.add_precedent({
            "decision_id": decision_id,
            "context": "Data pipeline",
            "outcome": "Easy to test and compose",
        })
        temp_graph.add_precedent({
            "decision_id": decision_id,
            "context": "API handlers",
            "outcome": "Clear data flow",
        })

        precedents = temp_graph.get_precedents_for_decision(decision_id)

        assert len(precedents) == 2

    def test_search_precedents(self, temp_graph):
        """Should search precedents by text."""
        decision_id = temp_graph.add_decision({"action": "Some decision"})
        temp_graph.add_precedent({
            "decision_id": decision_id,
            "context": "Building a web API",
            "outcome": "REST worked well for external clients",
        })

        results = temp_graph.search_precedents("web API REST", limit=5)

        assert len(results) >= 1


class TestOutcomesTable:
    """Test outcomes table operations."""

    def test_add_outcome(self, temp_graph):
        """Should add outcome to graph."""
        decision_id = temp_graph.add_decision({
            "action": "Chose microservices",
            "reasoning": "Need independent scaling",
        })

        outcome = {
            "decision_id": decision_id,
            "success": True,
            "feedback": "Deployment complexity increased but scaling improved",
            "impact": "positive",
        }

        doc_id = temp_graph.add_outcome(outcome)

        assert doc_id is not None
        assert doc_id.startswith("out_")

        retrieved = temp_graph.get_outcome(doc_id)
        assert retrieved is not None
        assert retrieved["success"] is True
        assert retrieved["impact"] == "positive"

    def test_get_outcome_for_decision(self, temp_graph):
        """Should get outcome for a specific decision."""
        decision_id = temp_graph.add_decision({
            "action": "Added caching layer",
        })

        temp_graph.add_outcome({
            "decision_id": decision_id,
            "success": True,
            "feedback": "Response times improved 10x",
            "impact": "positive",
        })

        outcome = temp_graph.get_outcome_for_decision(decision_id)

        assert outcome is not None
        assert outcome["decision_id"] == decision_id
        assert outcome["success"] is True

    def test_search_outcomes(self, temp_graph):
        """Should search outcomes by text."""
        decision_id = temp_graph.add_decision({"action": "Some decision"})
        temp_graph.add_outcome({
            "decision_id": decision_id,
            "success": False,
            "feedback": "Memory usage increased significantly",
            "impact": "negative",
        })

        results = temp_graph.search_outcomes("memory usage", limit=5)

        assert len(results) >= 1


class TestAutonomyTable:
    """Test autonomy table operations."""

    def test_add_autonomy(self, temp_graph):
        """Should add autonomy level to graph."""
        autonomy = {
            "action_type": "file_edit",
            "level": "suggest",
            "confidence": 0.75,
            "sample_count": 10,
        }

        doc_id = temp_graph.add_autonomy(autonomy)

        assert doc_id is not None
        assert doc_id.startswith("aut_")

        retrieved = temp_graph.get_autonomy(doc_id)
        assert retrieved is not None
        assert retrieved["action_type"] == "file_edit"
        assert retrieved["level"] == "suggest"

    def test_get_autonomy_for_action(self, temp_graph):
        """Should get autonomy for specific action type."""
        temp_graph.add_autonomy({
            "action_type": "commit",
            "level": "auto",
            "confidence": 0.95,
            "sample_count": 50,
        })

        autonomy = temp_graph.get_autonomy_for_action("commit")

        assert autonomy is not None
        assert autonomy["action_type"] == "commit"
        assert autonomy["level"] == "auto"

    def test_update_autonomy(self, temp_graph):
        """Should update existing autonomy when adding same action type."""
        # Add initial
        temp_graph.add_autonomy({
            "action_type": "refactor",
            "level": "ask",
            "confidence": 0.3,
            "sample_count": 5,
        })

        # Add again with same action_type should update
        temp_graph.add_autonomy({
            "action_type": "refactor",
            "level": "suggest",
            "confidence": 0.7,
            "sample_count": 20,
        })

        autonomy = temp_graph.get_autonomy_for_action("refactor")

        assert autonomy["level"] == "suggest"
        assert abs(autonomy["confidence"] - 0.7) < 0.001
        assert autonomy["sample_count"] == 20

    def test_get_all_autonomy(self, temp_graph):
        """Should get all autonomy levels."""
        temp_graph.add_autonomy({
            "action_type": "file_edit",
            "level": "suggest",
        })
        temp_graph.add_autonomy({
            "action_type": "commit",
            "level": "auto",
        })
        temp_graph.add_autonomy({
            "action_type": "refactor",
            "level": "ask",
        })

        all_autonomy = temp_graph.get_all_autonomy()

        assert len(all_autonomy) == 3
        action_types = {a["action_type"] for a in all_autonomy}
        assert action_types == {"file_edit", "commit", "refactor"}


class TestNewTablesInCounts:
    """Test that new tables are included in counts."""

    def test_counts_include_new_tables(self, temp_graph):
        """Should include all tables in counts."""
        counts = temp_graph.get_counts()

        expected_tables = {
            "decisions", "entities", "patterns", "memories",
            "policies", "exceptions", "precedents", "outcomes", "autonomy"
        }
        assert set(counts.keys()) == expected_tables

    def test_new_tables_in_list(self, temp_graph):
        """Should list all tables including new ones."""
        tables = set(temp_graph.list_tables())

        expected_tables = {
            "decisions", "entities", "patterns", "memories",
            "policies", "exceptions", "precedents", "outcomes", "autonomy"
        }
        assert expected_tables.issubset(tables)
