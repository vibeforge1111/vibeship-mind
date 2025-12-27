"""Tests for memory reinforcement system."""
from datetime import datetime
import pytest

from mind.v3.memory.reinforcement import (
    ReinforcementManager,
    ReinforcementConfig,
    FeedbackType,
    ReinforcementEvent,
)
from mind.v3.memory.working_memory import MemoryItem, MemoryType


class TestReinforcementConfig:
    """Test ReinforcementConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = ReinforcementConfig()

        assert config.retrieval_boost == 0.1
        assert config.positive_boost == 0.2
        assert config.negative_penalty == 0.1
        assert config.max_activation == 1.0

    def test_custom_config(self):
        """Should accept custom settings."""
        config = ReinforcementConfig(
            retrieval_boost=0.15,
            positive_boost=0.25,
        )

        assert config.retrieval_boost == 0.15


class TestFeedbackType:
    """Test FeedbackType enum."""

    def test_feedback_types_exist(self):
        """Should have all feedback types."""
        assert FeedbackType.RETRIEVAL
        assert FeedbackType.POSITIVE
        assert FeedbackType.NEGATIVE
        assert FeedbackType.CORRECTION


class TestReinforcementEvent:
    """Test ReinforcementEvent dataclass."""

    def test_create_event(self):
        """Should create reinforcement event."""
        event = ReinforcementEvent(
            item_id="mem-1",
            feedback_type=FeedbackType.POSITIVE,
            amount=0.2,
        )

        assert event.item_id == "mem-1"
        assert event.feedback_type == FeedbackType.POSITIVE
        assert event.amount == 0.2

    def test_event_has_timestamp(self):
        """Should have timestamp."""
        event = ReinforcementEvent(
            item_id="mem-1",
            feedback_type=FeedbackType.RETRIEVAL,
            amount=0.1,
        )

        assert event.timestamp is not None


class TestReinforcementManager:
    """Test ReinforcementManager."""

    @pytest.fixture
    def manager(self):
        """Create reinforcement manager."""
        return ReinforcementManager()

    def test_create_manager(self, manager):
        """Should create manager."""
        assert manager is not None

    def test_reinforce_on_retrieval(self, manager):
        """Should boost activation on retrieval."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.DECISION,
            activation=0.5,
        )

        reinforced = manager.on_retrieval(item)

        assert reinforced.activation > item.activation

    def test_reinforce_positive_feedback(self, manager):
        """Should boost on positive feedback."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.DECISION,
            activation=0.5,
        )

        reinforced = manager.on_positive_feedback(item)

        assert reinforced.activation > item.activation

    def test_penalize_negative_feedback(self, manager):
        """Should reduce activation on negative feedback."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.DECISION,
            activation=0.5,
        )

        penalized = manager.on_negative_feedback(item)

        assert penalized.activation < item.activation

    def test_activation_caps_at_max(self, manager):
        """Should not exceed max activation."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.DECISION,
            activation=0.95,
        )

        reinforced = manager.on_positive_feedback(item)

        assert reinforced.activation <= 1.0

    def test_activation_has_minimum(self, manager):
        """Should not go below minimum."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.DECISION,
            activation=0.05,
        )

        penalized = manager.on_negative_feedback(item)

        assert penalized.activation >= 0.0

    def test_apply_reinforcement(self, manager):
        """Should apply reinforcement event."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.DECISION,
            activation=0.5,
        )

        event = ReinforcementEvent(
            item_id="mem-1",
            feedback_type=FeedbackType.POSITIVE,
            amount=0.3,
        )

        reinforced = manager.apply(item, event)

        assert reinforced.activation == 0.8


class TestReinforcementTracking:
    """Test reinforcement tracking features."""

    @pytest.fixture
    def manager(self):
        """Create manager with tracking enabled."""
        config = ReinforcementConfig(track_history=True)
        return ReinforcementManager(config=config)

    def test_tracks_reinforcement_history(self, manager):
        """Should track reinforcement events."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.DECISION,
            activation=0.5,
        )

        manager.on_retrieval(item)
        manager.on_positive_feedback(item)

        history = manager.get_history("mem-1")

        assert len(history) == 2

    def test_get_reinforcement_stats(self, manager):
        """Should calculate stats for an item."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.DECISION,
            activation=0.5,
        )

        # Multiple reinforcements
        for _ in range(3):
            manager.on_retrieval(item)
        manager.on_positive_feedback(item)
        manager.on_negative_feedback(item)

        stats = manager.get_stats("mem-1")

        assert stats["retrieval_count"] == 3
        assert stats["positive_count"] == 1
        assert stats["negative_count"] == 1
        assert stats["net_reinforcement"] > 0  # More positive than negative


class TestConfidenceTracking:
    """Test prediction confidence tracking."""

    @pytest.fixture
    def manager(self):
        """Create manager."""
        return ReinforcementManager()

    def test_boost_importance_on_confirmation(self, manager):
        """Confirmed predictions should boost importance."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.PATTERN,
            importance=0.5,
        )

        boosted = manager.on_prediction_confirmed(item)

        assert boosted.importance > item.importance

    def test_reduce_importance_on_failure(self, manager):
        """Failed predictions should reduce importance."""
        item = MemoryItem(
            id="mem-1",
            content="Test",
            memory_type=MemoryType.PATTERN,
            importance=0.5,
        )

        reduced = manager.on_prediction_failed(item)

        assert reduced.importance < item.importance
