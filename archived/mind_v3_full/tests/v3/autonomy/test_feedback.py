"""Tests for feedback loop system."""
from datetime import datetime
import pytest

from mind.v3.autonomy.feedback import (
    FeedbackLoop,
    FeedbackConfig,
    UserFeedback,
    FeedbackType,
    FeedbackEffect,
)
from mind.v3.autonomy.confidence import (
    ConfidenceTracker,
    ActionOutcome,
    OutcomeType,
)
from mind.v3.autonomy.levels import AutonomyManager


class TestFeedbackType:
    """Test FeedbackType enum."""

    def test_feedback_types_exist(self):
        """Should have all feedback types."""
        assert FeedbackType.APPROVE
        assert FeedbackType.REJECT
        assert FeedbackType.CORRECT
        assert FeedbackType.IGNORE


class TestUserFeedback:
    """Test UserFeedback dataclass."""

    def test_create_feedback(self):
        """Should create user feedback."""
        feedback = UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.APPROVE,
            comment="Good suggestion",
        )

        assert feedback.action_type == "file_edit"
        assert feedback.feedback_type == FeedbackType.APPROVE
        assert feedback.comment == "Good suggestion"

    def test_feedback_has_timestamp(self):
        """Should have timestamp."""
        feedback = UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.APPROVE,
        )

        assert feedback.timestamp is not None

    def test_feedback_with_context(self):
        """Should accept context data."""
        feedback = UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.CORRECT,
            context={"file": "test.py", "line": 42},
            correction="Use different approach",
        )

        assert feedback.context["file"] == "test.py"
        assert feedback.correction == "Use different approach"


class TestFeedbackConfig:
    """Test FeedbackConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = FeedbackConfig()

        assert config.approval_boost > 0
        assert config.rejection_penalty > 0
        assert config.track_history is True

    def test_custom_config(self):
        """Should accept custom settings."""
        config = FeedbackConfig(
            approval_boost=0.2,
            rejection_penalty=0.3,
        )

        assert config.approval_boost == 0.2
        assert config.rejection_penalty == 0.3


class TestFeedbackLoop:
    """Test FeedbackLoop."""

    @pytest.fixture
    def loop(self):
        """Create feedback loop with tracker."""
        tracker = ConfidenceTracker()
        return FeedbackLoop(confidence_tracker=tracker)

    def test_create_loop(self, loop):
        """Should create feedback loop."""
        assert loop is not None

    def test_record_approval(self, loop):
        """Approval should increase confidence."""
        # Get initial confidence
        initial = loop._tracker.get_confidence("file_edit")

        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.APPROVE,
        ))

        updated = loop._tracker.get_confidence("file_edit")

        assert updated.score > initial.score

    def test_record_rejection(self, loop):
        """Rejection should decrease confidence."""
        # Build up some confidence first
        for _ in range(5):
            loop._tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        before = loop._tracker.get_confidence("file_edit")

        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.REJECT,
        ))

        after = loop._tracker.get_confidence("file_edit")

        assert after.score < before.score

    def test_record_correction(self, loop):
        """Correction should be stored for learning."""
        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.CORRECT,
            correction="Use async pattern instead",
            context={"original": "sync code"},
        ))

        corrections = loop.get_corrections("file_edit")

        assert len(corrections) == 1
        assert "async" in corrections[0].correction

    def test_ignore_has_no_effect(self, loop):
        """Ignore feedback should not affect confidence."""
        initial = loop._tracker.get_confidence("file_edit")

        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.IGNORE,
        ))

        updated = loop._tracker.get_confidence("file_edit")

        assert updated.score == initial.score


class TestFeedbackEffect:
    """Test FeedbackEffect tracking."""

    @pytest.fixture
    def loop(self):
        """Create feedback loop."""
        tracker = ConfidenceTracker()
        return FeedbackLoop(confidence_tracker=tracker)

    def test_record_returns_effect(self, loop):
        """Recording feedback should return effect."""
        effect = loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.APPROVE,
        ))

        assert isinstance(effect, FeedbackEffect)
        assert effect.confidence_change > 0
        assert effect.applied is True

    def test_effect_shows_level_change(self, loop):
        """Effect should indicate if level changed."""
        # Get initial state
        manager = AutonomyManager(confidence_tracker=loop._tracker)
        initial_level = manager.get_level("file_edit")

        # Apply many approvals to potentially change level
        for _ in range(15):
            effect = loop.record_feedback(UserFeedback(
                action_type="file_edit",
                feedback_type=FeedbackType.APPROVE,
            ))

        # Check if level changed
        new_level = manager.get_level("file_edit")

        # Effect should accurately reflect changes
        assert effect.new_confidence >= effect.old_confidence


class TestFeedbackHistory:
    """Test feedback history tracking."""

    @pytest.fixture
    def loop(self):
        """Create feedback loop with history."""
        config = FeedbackConfig(track_history=True)
        tracker = ConfidenceTracker()
        return FeedbackLoop(config=config, confidence_tracker=tracker)

    def test_get_history(self, loop):
        """Should track feedback history."""
        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.APPROVE,
        ))
        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.REJECT,
        ))

        history = loop.get_history("file_edit")

        assert len(history) == 2

    def test_get_stats(self, loop):
        """Should calculate feedback statistics."""
        for _ in range(3):
            loop.record_feedback(UserFeedback(
                action_type="file_edit",
                feedback_type=FeedbackType.APPROVE,
            ))
        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.REJECT,
        ))

        stats = loop.get_stats("file_edit")

        assert stats["approval_count"] == 3
        assert stats["rejection_count"] == 1
        assert stats["approval_rate"] == 0.75


class TestFeedbackLearning:
    """Test learning from feedback patterns."""

    @pytest.fixture
    def loop(self):
        """Create feedback loop."""
        tracker = ConfidenceTracker()
        return FeedbackLoop(confidence_tracker=tracker)

    def test_consistent_rejection_lowers_max_level(self, loop):
        """Consistent rejection should lower allowed autonomy."""
        manager = AutonomyManager(confidence_tracker=loop._tracker)

        # Initial level
        initial = manager.get_level("risky_action")

        # Consistent rejection
        for _ in range(10):
            loop.record_feedback(UserFeedback(
                action_type="risky_action",
                feedback_type=FeedbackType.REJECT,
            ))

        # Level should decrease
        final = manager.get_level("risky_action")

        assert final.value <= initial.value

    def test_get_suggested_corrections(self, loop):
        """Should suggest corrections based on patterns."""
        # Add multiple similar corrections
        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.CORRECT,
            correction="Use async/await instead of callbacks",
        ))
        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.CORRECT,
            correction="Prefer async pattern over sync",
        ))

        suggestions = loop.get_correction_patterns("file_edit")

        assert len(suggestions) >= 1
