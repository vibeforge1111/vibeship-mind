"""Tests for memory decay system."""
from datetime import datetime, timedelta
import pytest

from mind.v3.memory.decay import (
    DecayManager,
    DecayConfig,
    DecayCurve,
)
from mind.v3.memory.working_memory import MemoryItem, MemoryType


class TestDecayConfig:
    """Test DecayConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = DecayConfig()

        assert config.curve == DecayCurve.EXPONENTIAL
        assert config.half_life_hours == 24
        assert config.min_activation == 0.01

    def test_custom_config(self):
        """Should accept custom settings."""
        config = DecayConfig(
            curve=DecayCurve.LINEAR,
            half_life_hours=48,
        )

        assert config.curve == DecayCurve.LINEAR
        assert config.half_life_hours == 48


class TestDecayCurve:
    """Test DecayCurve enum."""

    def test_curves_exist(self):
        """Should have all curve types."""
        assert DecayCurve.LINEAR
        assert DecayCurve.EXPONENTIAL
        assert DecayCurve.POWER_LAW


class TestDecayManager:
    """Test DecayManager."""

    @pytest.fixture
    def manager(self):
        """Create decay manager."""
        return DecayManager()

    def test_create_manager(self, manager):
        """Should create decay manager."""
        assert manager is not None

    def test_calculate_decay_exponential(self, manager):
        """Should calculate exponential decay."""
        # After 1 half-life, activation should be ~0.5
        config = DecayConfig(
            curve=DecayCurve.EXPONENTIAL,
            half_life_hours=24,
            importance_factor=0.0,  # Disable importance for this test
        )
        manager = DecayManager(config=config)

        initial_activation = 1.0
        hours_elapsed = 24  # 1 half-life

        decayed = manager.calculate_decay(
            initial_activation=initial_activation,
            hours_elapsed=hours_elapsed,
            importance=0.0,  # No importance boost
        )

        # Should be approximately 0.5 (within tolerance)
        assert 0.45 <= decayed <= 0.55

    def test_calculate_decay_linear(self):
        """Should calculate linear decay."""
        config = DecayConfig(
            curve=DecayCurve.LINEAR,
            half_life_hours=24,
        )
        manager = DecayManager(config=config)

        initial = 1.0
        hours = 12  # Half of half-life

        decayed = manager.calculate_decay(initial, hours)

        # Linear decay: should lose 25% in half the half-life time
        assert 0.7 <= decayed <= 0.8

    def test_calculate_decay_respects_minimum(self):
        """Should not decay below minimum."""
        config = DecayConfig(min_activation=0.1)
        manager = DecayManager(config=config)

        # Very long time
        decayed = manager.calculate_decay(1.0, hours_elapsed=10000)

        assert decayed >= 0.1

    def test_apply_decay_to_item(self, manager):
        """Should apply decay to memory item."""
        # Create item with old access time
        item = MemoryItem(
            id="mem-1",
            content="Old memory",
            memory_type=MemoryType.EVENT,
            activation=1.0,
            accessed_at=datetime.now() - timedelta(hours=48),
        )

        decayed_item = manager.apply_decay(item)

        assert decayed_item.activation < item.activation

    def test_importance_modulates_decay(self):
        """Important items should decay slower."""
        config = DecayConfig(importance_factor=0.5)
        manager = DecayManager(config=config)

        # Two items with different importance
        important = MemoryItem(
            id="m1",
            content="Important",
            memory_type=MemoryType.DECISION,
            activation=1.0,
            importance=0.9,
            accessed_at=datetime.now() - timedelta(hours=24),
        )
        trivial = MemoryItem(
            id="m2",
            content="Trivial",
            memory_type=MemoryType.EVENT,
            activation=1.0,
            importance=0.1,
            accessed_at=datetime.now() - timedelta(hours=24),
        )

        decayed_important = manager.apply_decay(important)
        decayed_trivial = manager.apply_decay(trivial)

        # Important item should retain more activation
        assert decayed_important.activation > decayed_trivial.activation

    def test_apply_decay_batch(self, manager):
        """Should apply decay to multiple items."""
        items = [
            MemoryItem(
                id=f"mem-{i}",
                content=f"Memory {i}",
                memory_type=MemoryType.EVENT,
                activation=1.0,
                accessed_at=datetime.now() - timedelta(hours=i * 12),
            )
            for i in range(1, 4)
        ]

        decayed = manager.apply_decay_batch(items)

        # All should have lower activation
        for original, result in zip(items, decayed):
            assert result.activation <= original.activation

        # Later items should have decayed more
        assert decayed[0].activation > decayed[1].activation > decayed[2].activation


class TestDecayScheduling:
    """Test decay scheduling features."""

    def test_should_archive_threshold(self):
        """Should identify items for archival."""
        config = DecayConfig(archive_threshold=0.05)
        manager = DecayManager(config=config)

        item = MemoryItem(
            id="mem-1",
            content="Very old",
            memory_type=MemoryType.EVENT,
            activation=0.03,
        )

        assert manager.should_archive(item) is True

    def test_should_not_archive_active(self):
        """Should not archive active items."""
        config = DecayConfig(archive_threshold=0.05)
        manager = DecayManager(config=config)

        item = MemoryItem(
            id="mem-1",
            content="Recent",
            memory_type=MemoryType.EVENT,
            activation=0.8,
        )

        assert manager.should_archive(item) is False

    def test_time_until_archive(self):
        """Should estimate time until archival."""
        config = DecayConfig(
            half_life_hours=24,
            archive_threshold=0.1,
            importance_factor=0.0,  # Disable importance for predictable test
        )
        manager = DecayManager(config=config)

        item = MemoryItem(
            id="mem-1",
            content="Memory",
            memory_type=MemoryType.EVENT,
            activation=1.0,
            importance=0.0,  # No importance boost
        )

        hours = manager.hours_until_archive(item)

        # Should be approximately 3.3 half-lives to go from 1.0 to 0.1
        # (2^-3.3 ≈ 0.1)
        assert 70 < hours < 90  # ~80 hours = 3.3 * 24
