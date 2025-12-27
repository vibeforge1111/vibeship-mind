"""Tests for working memory."""
from datetime import datetime, timedelta
import pytest

from mind.v3.memory.working_memory import (
    WorkingMemory,
    WorkingMemoryConfig,
    MemoryItem,
    MemoryType,
)


class TestWorkingMemoryConfig:
    """Test WorkingMemoryConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = WorkingMemoryConfig()

        assert config.capacity == 7  # Miller's law
        assert config.default_ttl_seconds == 3600  # 1 hour
        assert config.min_activation == 0.0
        assert config.max_activation == 1.0

    def test_custom_config(self):
        """Should accept custom settings."""
        config = WorkingMemoryConfig(
            capacity=10,
            default_ttl_seconds=7200,
        )

        assert config.capacity == 10
        assert config.default_ttl_seconds == 7200


class TestMemoryItem:
    """Test MemoryItem dataclass."""

    def test_create_memory_item(self):
        """Should create memory item."""
        item = MemoryItem(
            id="mem-1",
            content="Test decision",
            memory_type=MemoryType.DECISION,
            activation=1.0,
            importance=0.8,
        )

        assert item.id == "mem-1"
        assert item.content == "Test decision"
        assert item.memory_type == MemoryType.DECISION

    def test_memory_item_defaults(self):
        """Should have reasonable defaults."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
        )

        assert item.activation == 1.0
        assert item.importance == 0.5
        assert item.metadata == {}

    def test_memory_item_with_metadata(self):
        """Should support metadata."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
            metadata={"source": "user", "tags": ["important"]},
        )

        assert item.metadata["source"] == "user"


class TestMemoryType:
    """Test MemoryType enum."""

    def test_memory_types_exist(self):
        """Should have all required memory types."""
        assert MemoryType.EVENT
        assert MemoryType.DECISION
        assert MemoryType.LEARNING
        assert MemoryType.PATTERN
        assert MemoryType.REMINDER


class TestWorkingMemory:
    """Test WorkingMemory."""

    @pytest.fixture
    def memory(self):
        """Create working memory instance."""
        return WorkingMemory()

    def test_create_working_memory(self, memory):
        """Should create working memory."""
        assert memory is not None
        assert memory.size == 0

    def test_add_item(self, memory):
        """Should add item to memory."""
        item = MemoryItem(
            id="mem-1",
            content="User prefers tabs",
            memory_type=MemoryType.DECISION,
        )

        memory.add(item)

        assert memory.size == 1
        assert memory.get("mem-1") is not None

    def test_add_updates_existing(self, memory):
        """Should update existing item."""
        item1 = MemoryItem(
            id="mem-1",
            content="Original",
            memory_type=MemoryType.EVENT,
        )
        item2 = MemoryItem(
            id="mem-1",
            content="Updated",
            memory_type=MemoryType.EVENT,
        )

        memory.add(item1)
        memory.add(item2)

        assert memory.size == 1
        assert memory.get("mem-1").content == "Updated"

    def test_add_respects_capacity(self):
        """Should respect capacity limit."""
        config = WorkingMemoryConfig(capacity=3)
        memory = WorkingMemory(config=config)

        # Add 4 items
        for i in range(4):
            memory.add(MemoryItem(
                id=f"mem-{i}",
                content=f"Item {i}",
                memory_type=MemoryType.EVENT,
                importance=0.1 * i,  # Increasing importance
            ))

        # Should only keep 3 (highest importance)
        assert memory.size == 3
        # Lowest importance item should be evicted
        assert memory.get("mem-0") is None

    def test_get_item(self, memory):
        """Should retrieve item by ID."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
        )
        memory.add(item)

        retrieved = memory.get("mem-1")

        assert retrieved is not None
        assert retrieved.content == "Test"

    def test_get_missing_item(self, memory):
        """Should return None for missing item."""
        assert memory.get("nonexistent") is None

    def test_get_boosts_activation(self, memory):
        """Should boost activation when accessed."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
            activation=0.5,
        )
        memory.add(item)

        # Access the item
        memory.get("mem-1")

        # Activation should increase
        assert memory.get("mem-1").activation > 0.5

    def test_remove_item(self, memory):
        """Should remove item from memory."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
        )
        memory.add(item)

        removed = memory.remove("mem-1")

        assert removed is True
        assert memory.size == 0

    def test_remove_missing_item(self, memory):
        """Should return False for missing item."""
        assert memory.remove("nonexistent") is False

    def test_clear_memory(self, memory):
        """Should clear all items."""
        for i in range(3):
            memory.add(MemoryItem(
                id=f"mem-{i}",
                content=f"Item {i}",
                memory_type=MemoryType.EVENT,
            ))

        memory.clear()

        assert memory.size == 0

    def test_list_items(self, memory):
        """Should list all items."""
        for i in range(3):
            memory.add(MemoryItem(
                id=f"mem-{i}",
                content=f"Item {i}",
                memory_type=MemoryType.EVENT,
            ))

        items = memory.list()

        assert len(items) == 3

    def test_list_by_type(self, memory):
        """Should filter by memory type."""
        memory.add(MemoryItem(
            id="mem-1",
            content="Decision 1",
            memory_type=MemoryType.DECISION,
        ))
        memory.add(MemoryItem(
            id="mem-2",
            content="Event 1",
            memory_type=MemoryType.EVENT,
        ))

        decisions = memory.list(memory_type=MemoryType.DECISION)

        assert len(decisions) == 1
        assert decisions[0].memory_type == MemoryType.DECISION


class TestWorkingMemoryActivation:
    """Test activation mechanics."""

    @pytest.fixture
    def memory(self):
        """Create working memory instance."""
        return WorkingMemory()

    def test_initial_activation(self, memory):
        """New items should have full activation."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
        )
        memory.add(item)

        assert memory.get("mem-1").activation == 1.0

    def test_decay_activation(self, memory):
        """Should decay activation over time."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
            activation=1.0,
        )
        memory.add(item)

        # Simulate time passing
        memory.decay(decay_factor=0.1)

        # Use peek() to check without boosting activation
        assert memory.peek("mem-1").activation < 1.0

    def test_decay_respects_importance(self, memory):
        """Important items should decay slower."""
        memory.add(MemoryItem(
            id="mem-high",
            content="Important",
            memory_type=MemoryType.DECISION,
            importance=0.9,
        ))
        memory.add(MemoryItem(
            id="mem-low",
            content="Trivial",
            memory_type=MemoryType.EVENT,
            importance=0.1,
        ))

        # Decay both
        memory.decay(decay_factor=0.5)

        # Use peek() to check without boosting activation
        high = memory.peek("mem-high")
        low = memory.peek("mem-low")

        # High importance should retain more activation
        assert high.activation > low.activation

    def test_reinforce_activation(self, memory):
        """Should reinforce item activation."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
            activation=0.5,
        )
        memory.add(item)

        memory.reinforce("mem-1", amount=0.3)

        # Use peek() to check without boosting activation
        assert memory.peek("mem-1").activation == 0.8

    def test_reinforce_caps_at_max(self, memory):
        """Reinforcement should not exceed max activation."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
            activation=0.9,
        )
        memory.add(item)

        memory.reinforce("mem-1", amount=0.5)

        # Use peek() to check without boosting activation
        assert memory.peek("mem-1").activation == 1.0


class TestWorkingMemorySnapshot:
    """Test memory state snapshots."""

    def test_snapshot_creates_copy(self):
        """Snapshot should create independent copy."""
        memory = WorkingMemory()
        memory.add(MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.EVENT,
        ))

        snapshot = memory.snapshot()

        # Modify original
        memory.add(MemoryItem(
            id="mem-2",
            content="New",
            memory_type=MemoryType.EVENT,
        ))

        # Snapshot should be unchanged
        assert len(snapshot) == 1

    def test_restore_from_snapshot(self):
        """Should restore state from snapshot."""
        memory = WorkingMemory()
        memory.add(MemoryItem(
            id="mem-1",
            content="Original",
            memory_type=MemoryType.EVENT,
        ))

        snapshot = memory.snapshot()

        # Modify
        memory.clear()
        memory.add(MemoryItem(
            id="mem-2",
            content="New",
            memory_type=MemoryType.EVENT,
        ))

        # Restore
        memory.restore(snapshot)

        assert memory.size == 1
        assert memory.get("mem-1") is not None
        assert memory.get("mem-2") is None
