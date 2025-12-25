"""Tests for autonomy levels system."""
import pytest

from mind.v3.autonomy.levels import (
    AutonomyLevel,
    AutonomyManager,
    AutonomyConfig,
    ActionPolicy,
)
from mind.v3.autonomy.confidence import (
    ConfidenceTracker,
    ActionOutcome,
    OutcomeType,
)


class TestAutonomyLevel:
    """Test AutonomyLevel enum."""

    def test_levels_exist(self):
        """Should have all autonomy levels."""
        assert AutonomyLevel.RECORD_ONLY
        assert AutonomyLevel.SUGGEST
        assert AutonomyLevel.ASK_PERMISSION
        assert AutonomyLevel.ACT_NOTIFY
        assert AutonomyLevel.SILENT

    def test_level_ordering(self):
        """Levels should be ordered by autonomy."""
        assert AutonomyLevel.RECORD_ONLY.value < AutonomyLevel.SUGGEST.value
        assert AutonomyLevel.SUGGEST.value < AutonomyLevel.ASK_PERMISSION.value
        assert AutonomyLevel.ASK_PERMISSION.value < AutonomyLevel.ACT_NOTIFY.value
        assert AutonomyLevel.ACT_NOTIFY.value < AutonomyLevel.SILENT.value


class TestAutonomyConfig:
    """Test AutonomyConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = AutonomyConfig()

        assert config.default_level == AutonomyLevel.SUGGEST
        assert config.max_level == AutonomyLevel.ACT_NOTIFY
        assert len(config.level_thresholds) > 0

    def test_custom_thresholds(self):
        """Should accept custom thresholds."""
        config = AutonomyConfig(
            level_thresholds={
                AutonomyLevel.ACT_NOTIFY: 0.9,
                AutonomyLevel.ASK_PERMISSION: 0.7,
            }
        )

        assert config.level_thresholds[AutonomyLevel.ACT_NOTIFY] == 0.9


class TestActionPolicy:
    """Test ActionPolicy dataclass."""

    def test_create_policy(self):
        """Should create action policy."""
        policy = ActionPolicy(
            action_type="file_edit",
            current_level=AutonomyLevel.SUGGEST,
            max_allowed_level=AutonomyLevel.ACT_NOTIFY,
            confidence=0.75,
        )

        assert policy.action_type == "file_edit"
        assert policy.current_level == AutonomyLevel.SUGGEST
        assert policy.confidence == 0.75

    def test_policy_allows_action(self):
        """Should check if action is allowed at level."""
        policy = ActionPolicy(
            action_type="file_edit",
            current_level=AutonomyLevel.ASK_PERMISSION,
            max_allowed_level=AutonomyLevel.ACT_NOTIFY,
            confidence=0.8,
        )

        # Can act at or below current level
        assert policy.allows(AutonomyLevel.RECORD_ONLY)
        assert policy.allows(AutonomyLevel.SUGGEST)
        assert policy.allows(AutonomyLevel.ASK_PERMISSION)

        # Cannot act above current level
        assert not policy.allows(AutonomyLevel.ACT_NOTIFY)
        assert not policy.allows(AutonomyLevel.SILENT)


class TestAutonomyManager:
    """Test AutonomyManager."""

    @pytest.fixture
    def manager(self):
        """Create autonomy manager."""
        return AutonomyManager()

    def test_create_manager(self, manager):
        """Should create manager."""
        assert manager is not None

    def test_get_default_level(self, manager):
        """Should return default level for unknown action."""
        level = manager.get_level("unknown_action")

        assert level == AutonomyLevel.SUGGEST  # default

    def test_level_increases_with_confidence(self):
        """Higher confidence should allow higher autonomy."""
        tracker = ConfidenceTracker()
        manager = AutonomyManager(confidence_tracker=tracker)

        # Record many successes to build confidence
        for _ in range(20):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        level = manager.get_level("file_edit")

        # High confidence should enable higher autonomy
        assert level.value >= AutonomyLevel.ASK_PERMISSION.value

    def test_level_decreases_with_failures(self):
        """Failures should reduce autonomy."""
        tracker = ConfidenceTracker()
        manager = AutonomyManager(confidence_tracker=tracker)

        # Build up confidence first
        for _ in range(10):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        before = manager.get_level("file_edit")

        # Now fail repeatedly
        for _ in range(15):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.FAILURE,
            ))

        after = manager.get_level("file_edit")

        assert after.value <= before.value

    def test_respects_max_level(self):
        """Should never exceed configured max level."""
        config = AutonomyConfig(max_level=AutonomyLevel.ASK_PERMISSION)
        tracker = ConfidenceTracker()
        manager = AutonomyManager(config=config, confidence_tracker=tracker)

        # Build very high confidence
        for _ in range(100):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        level = manager.get_level("file_edit")

        assert level.value <= AutonomyLevel.ASK_PERMISSION.value


class TestAutonomyPolicies:
    """Test action-specific policies."""

    @pytest.fixture
    def manager(self):
        """Create manager with tracker."""
        tracker = ConfidenceTracker()
        return AutonomyManager(confidence_tracker=tracker)

    def test_get_policy(self, manager):
        """Should return policy for action type."""
        policy = manager.get_policy("file_edit")

        assert policy.action_type == "file_edit"
        assert policy.current_level is not None
        assert policy.confidence is not None

    def test_set_action_max_level(self, manager):
        """Should set max level for specific action."""
        # Restrict git operations to lower autonomy
        manager.set_action_max_level("git_push", AutonomyLevel.ASK_PERMISSION)

        policy = manager.get_policy("git_push")

        assert policy.max_allowed_level == AutonomyLevel.ASK_PERMISSION

    def test_override_level(self, manager):
        """Should allow manual level override."""
        manager.override_level("sensitive_action", AutonomyLevel.RECORD_ONLY)

        level = manager.get_level("sensitive_action")

        assert level == AutonomyLevel.RECORD_ONLY


class TestAutonomyDescriptions:
    """Test level descriptions and guidance."""

    @pytest.fixture
    def manager(self):
        """Create autonomy manager."""
        return AutonomyManager()

    def test_level_has_description(self, manager):
        """Each level should have a description."""
        for level in AutonomyLevel:
            desc = manager.get_level_description(level)
            assert desc is not None
            assert len(desc) > 0

    def test_level_has_guidance(self, manager):
        """Each level should have action guidance."""
        for level in AutonomyLevel:
            guidance = manager.get_level_guidance(level)
            assert guidance is not None


class TestAutonomySummary:
    """Test autonomy summary and reporting."""

    @pytest.fixture
    def manager(self):
        """Create manager with some history."""
        tracker = ConfidenceTracker()
        manager = AutonomyManager(confidence_tracker=tracker)

        # Add some history
        for _ in range(5):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))
        for _ in range(3):
            tracker.record_outcome(ActionOutcome(
                action_type="git_commit",
                outcome=OutcomeType.FAILURE,
            ))

        return manager

    def test_get_summary(self, manager):
        """Should return autonomy summary."""
        summary = manager.get_summary()

        assert "file_edit" in summary
        assert "git_commit" in summary
        assert summary["file_edit"]["level"] is not None
        assert summary["git_commit"]["level"] is not None

    def test_list_high_autonomy_actions(self, manager):
        """Should list actions with high autonomy."""
        # file_edit has successes, should have higher level
        high_autonomy = manager.list_actions_at_level(AutonomyLevel.ASK_PERMISSION)

        # May or may not include file_edit depending on thresholds
        assert isinstance(high_autonomy, list)
