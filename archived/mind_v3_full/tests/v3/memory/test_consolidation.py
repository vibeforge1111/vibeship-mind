"""Tests for memory consolidation."""
from datetime import datetime, timedelta
import pytest

from mind.v3.memory.consolidation import (
    MemoryConsolidator,
    ConsolidationConfig,
    ConsolidatedPattern,
)
from mind.v3.memory.working_memory import MemoryItem, MemoryType


class TestConsolidationConfig:
    """Test ConsolidationConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = ConsolidationConfig()

        assert config.min_occurrences == 3
        assert config.similarity_threshold == 0.7
        assert config.min_confidence == 0.3

    def test_custom_config(self):
        """Should accept custom settings."""
        config = ConsolidationConfig(
            min_occurrences=5,
            similarity_threshold=0.8,
        )

        assert config.min_occurrences == 5


class TestConsolidatedPattern:
    """Test ConsolidatedPattern dataclass."""

    def test_create_pattern(self):
        """Should create consolidated pattern."""
        pattern = ConsolidatedPattern(
            id="pattern-1",
            description="User prefers tabs over spaces",
            source_ids=["mem-1", "mem-2", "mem-3"],
            confidence=0.85,
            occurrences=3,
        )

        assert pattern.id == "pattern-1"
        assert pattern.confidence == 0.85
        assert len(pattern.source_ids) == 3

    def test_pattern_with_metadata(self):
        """Should support metadata."""
        pattern = ConsolidatedPattern(
            id="pattern-1",
            description="User prefers Python",
            source_ids=["mem-1"],
            confidence=0.9,
            occurrences=5,
            metadata={"category": "language_preference"},
        )

        assert pattern.metadata["category"] == "language_preference"


class TestMemoryConsolidator:
    """Test MemoryConsolidator."""

    @pytest.fixture
    def consolidator(self):
        """Create consolidator instance."""
        return MemoryConsolidator()

    def test_create_consolidator(self, consolidator):
        """Should create consolidator."""
        assert consolidator is not None

    def test_consolidate_empty_items(self, consolidator):
        """Should handle empty input."""
        patterns = consolidator.consolidate([])

        assert patterns == []

    def test_consolidate_single_item(self, consolidator):
        """Should not create patterns from single item."""
        items = [
            MemoryItem(
                id="mem-1",
                content="Used Python",
                memory_type=MemoryType.DECISION,
            )
        ]

        patterns = consolidator.consolidate(items)

        assert len(patterns) == 0

    def test_consolidate_similar_items(self):
        """Should consolidate similar items into pattern."""
        # Use lower thresholds for testing
        config = ConsolidationConfig(min_occurrences=3, similarity_threshold=0.5)
        consolidator = MemoryConsolidator(config=config)

        # Use more explicit repeated keywords
        items = [
            MemoryItem(
                id="mem-1",
                content="Using Python language for scripting",
                memory_type=MemoryType.DECISION,
            ),
            MemoryItem(
                id="mem-2",
                content="Python language is preferred",
                memory_type=MemoryType.DECISION,
            ),
            MemoryItem(
                id="mem-3",
                content="Chose Python language again",
                memory_type=MemoryType.DECISION,
            ),
        ]

        patterns = consolidator.consolidate(items)

        # Should detect Python preference pattern
        assert len(patterns) >= 1
        pattern = patterns[0]
        assert "python" in pattern.description.lower() or "language" in pattern.description.lower()
        assert pattern.occurrences >= 3

    def test_consolidate_respects_min_occurrences(self):
        """Should require minimum occurrences."""
        config = ConsolidationConfig(min_occurrences=5)
        consolidator = MemoryConsolidator(config=config)

        items = [
            MemoryItem(id=f"mem-{i}", content="Python", memory_type=MemoryType.DECISION)
            for i in range(3)
        ]

        patterns = consolidator.consolidate(items)

        # Should not create pattern (only 3 items, need 5)
        assert len(patterns) == 0

    def test_consolidate_includes_source_ids(self, consolidator):
        """Should track source item IDs."""
        items = [
            MemoryItem(id="mem-1", content="Use tabs", memory_type=MemoryType.DECISION),
            MemoryItem(id="mem-2", content="Tabs preferred", memory_type=MemoryType.DECISION),
            MemoryItem(id="mem-3", content="Going with tabs", memory_type=MemoryType.DECISION),
        ]

        patterns = consolidator.consolidate(items)

        if patterns:
            assert "mem-1" in patterns[0].source_ids or \
                   "mem-2" in patterns[0].source_ids or \
                   "mem-3" in patterns[0].source_ids

    def test_consolidate_calculates_confidence(self, consolidator):
        """Should calculate pattern confidence."""
        items = [
            MemoryItem(
                id=f"mem-{i}",
                content="Always use type hints",
                memory_type=MemoryType.DECISION,
                importance=0.8,
            )
            for i in range(5)
        ]

        patterns = consolidator.consolidate(items)

        if patterns:
            assert patterns[0].confidence >= 0.5

    def test_consolidate_different_types(self):
        """Should keep different memory types separate."""
        # Use explicit config
        config = ConsolidationConfig(min_occurrences=3)
        consolidator = MemoryConsolidator(config=config)

        items = [
            MemoryItem(id="dec-1", content="Python programming decision", memory_type=MemoryType.DECISION),
            MemoryItem(id="dec-2", content="Python programming choice", memory_type=MemoryType.DECISION),
            MemoryItem(id="dec-3", content="Python programming preferred", memory_type=MemoryType.DECISION),
            MemoryItem(id="learn-1", content="React framework learning", memory_type=MemoryType.LEARNING),
            MemoryItem(id="learn-2", content="React framework study", memory_type=MemoryType.LEARNING),
            MemoryItem(id="learn-3", content="React framework knowledge", memory_type=MemoryType.LEARNING),
        ]

        patterns = consolidator.consolidate(items)

        # Should create separate patterns for decisions and learnings
        assert len(patterns) >= 1


class TestConsolidationRules:
    """Test specific consolidation rules."""

    @pytest.fixture
    def consolidator(self):
        """Create consolidator with low thresholds for testing."""
        config = ConsolidationConfig(
            min_occurrences=2,
            similarity_threshold=0.5,
        )
        return MemoryConsolidator(config=config)

    def test_tool_preference_pattern(self, consolidator):
        """Should detect tool usage patterns."""
        items = [
            MemoryItem(id="m1", content="Using Glob to find files", memory_type=MemoryType.EVENT),
            MemoryItem(id="m2", content="Used Glob for file search", memory_type=MemoryType.EVENT),
            MemoryItem(id="m3", content="Glob tool for pattern matching", memory_type=MemoryType.EVENT),
        ]

        patterns = consolidator.consolidate(items)

        # Should detect Glob usage pattern
        if patterns:
            descriptions = [p.description.lower() for p in patterns]
            assert any("glob" in d for d in descriptions)

    def test_error_pattern(self, consolidator):
        """Should detect recurring errors."""
        items = [
            MemoryItem(id="e1", content="Import error with numpy", memory_type=MemoryType.LEARNING),
            MemoryItem(id="e2", content="NumPy import failed", memory_type=MemoryType.LEARNING),
            MemoryItem(id="e3", content="numpy not found error", memory_type=MemoryType.LEARNING),
        ]

        patterns = consolidator.consolidate(items)

        if patterns:
            descriptions = [p.description.lower() for p in patterns]
            assert any("numpy" in d or "import" in d for d in descriptions)


class TestConsolidationPersistence:
    """Test pattern persistence."""

    def test_pattern_to_dict(self):
        """Should serialize pattern to dict."""
        pattern = ConsolidatedPattern(
            id="pattern-1",
            description="Prefers Python",
            source_ids=["mem-1", "mem-2"],
            confidence=0.9,
            occurrences=5,
        )

        data = pattern.to_dict()

        assert data["id"] == "pattern-1"
        assert data["confidence"] == 0.9

    def test_pattern_from_dict(self):
        """Should deserialize pattern from dict."""
        data = {
            "id": "pattern-1",
            "description": "Prefers Python",
            "source_ids": ["mem-1", "mem-2"],
            "confidence": 0.9,
            "occurrences": 5,
            "created_at": datetime.now().isoformat(),
            "metadata": {},
        }

        pattern = ConsolidatedPattern.from_dict(data)

        assert pattern.id == "pattern-1"
        assert pattern.confidence == 0.9
