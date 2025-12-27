"""Tests for memory domain models."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from mind.core.memory.models import Memory, TemporalLevel


class TestTemporalLevel:
    """Tests for TemporalLevel enum."""

    def test_level_ordering(self):
        """Levels should be ordered from immediate to identity."""
        assert TemporalLevel.IMMEDIATE < TemporalLevel.SITUATIONAL
        assert TemporalLevel.SITUATIONAL < TemporalLevel.SEASONAL
        assert TemporalLevel.SEASONAL < TemporalLevel.IDENTITY

    def test_level_values(self):
        """Levels should have expected integer values."""
        assert TemporalLevel.IMMEDIATE.value == 1
        assert TemporalLevel.SITUATIONAL.value == 2
        assert TemporalLevel.SEASONAL.value == 3
        assert TemporalLevel.IDENTITY.value == 4

    def test_level_descriptions(self):
        """Each level should have a description."""
        for level in TemporalLevel:
            assert level.description is not None
            assert len(level.description) > 0

    def test_typical_durations(self):
        """Higher levels should have longer durations."""
        durations = [level.typical_duration_days for level in TemporalLevel]
        assert durations == sorted(durations)


class TestMemory:
    """Tests for Memory domain model."""

    @pytest.fixture
    def sample_memory(self) -> Memory:
        """Create a sample memory for testing."""
        return Memory(
            memory_id=uuid4(),
            user_id=uuid4(),
            content="User prefers dark mode",
            content_type="preference",
            temporal_level=TemporalLevel.IDENTITY,
            valid_from=datetime.now(UTC),
            valid_until=None,
            base_salience=0.8,
            outcome_adjustment=0.05,
        )

    def test_effective_salience(self, sample_memory: Memory):
        """Effective salience combines base and adjustment."""
        assert sample_memory.effective_salience == 0.85

    def test_effective_salience_clamped(self):
        """Effective salience should be clamped to [0, 1]."""
        memory = Memory(
            memory_id=uuid4(),
            user_id=uuid4(),
            content="Test",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC),
            valid_until=None,
            base_salience=0.9,
            outcome_adjustment=0.5,  # Would exceed 1.0
        )
        assert memory.effective_salience == 1.0

        memory_low = Memory(
            memory_id=uuid4(),
            user_id=uuid4(),
            content="Test",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC),
            valid_until=None,
            base_salience=0.1,
            outcome_adjustment=-0.5,  # Would go below 0
        )
        assert memory_low.effective_salience == 0.0

    def test_is_valid_current(self, sample_memory: Memory):
        """Memory with no end date should be valid."""
        assert sample_memory.is_valid is True

    def test_is_valid_expired(self):
        """Expired memory should not be valid."""
        memory = Memory(
            memory_id=uuid4(),
            user_id=uuid4(),
            content="Test",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC) - timedelta(days=2),
            valid_until=datetime.now(UTC) - timedelta(days=1),
            base_salience=1.0,
        )
        assert memory.is_valid is False

    def test_is_valid_future(self):
        """Future memory should not be valid yet."""
        memory = Memory(
            memory_id=uuid4(),
            user_id=uuid4(),
            content="Test",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC) + timedelta(days=1),
            valid_until=None,
            base_salience=1.0,
        )
        assert memory.is_valid is False

    def test_with_outcome_adjustment(self, sample_memory: Memory):
        """Adjustment should create new memory with updated salience."""
        adjusted = sample_memory.with_outcome_adjustment(0.1)

        # Original unchanged
        assert sample_memory.outcome_adjustment == 0.05

        # New memory has adjusted value
        assert adjusted.outcome_adjustment == 0.15
        assert adjusted.memory_id == sample_memory.memory_id  # Same ID
        assert adjusted.content == sample_memory.content  # Same content

    def test_outcome_ratio_no_outcomes(self, sample_memory: Memory):
        """Outcome ratio should be None with no outcomes."""
        assert sample_memory.outcome_ratio is None

    def test_outcome_ratio_with_outcomes(self):
        """Outcome ratio should be calculated correctly."""
        memory = Memory(
            memory_id=uuid4(),
            user_id=uuid4(),
            content="Test",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC),
            valid_until=None,
            base_salience=1.0,
            positive_outcomes=3,
            negative_outcomes=1,
        )
        assert memory.outcome_ratio == 0.75

    def test_immutability(self, sample_memory: Memory):
        """Memory should be immutable."""
        with pytest.raises(AttributeError):
            sample_memory.content = "Changed"
