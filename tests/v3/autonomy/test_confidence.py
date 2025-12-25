"""Tests for confidence tracking system."""
from datetime import datetime, timedelta
import pytest

from mind.v3.autonomy.confidence import (
    ConfidenceTracker,
    ConfidenceConfig,
    ConfidenceScore,
    ActionOutcome,
    OutcomeType,
)


class TestConfidenceConfig:
    """Test ConfidenceConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = ConfidenceConfig()

        assert config.initial_confidence == 0.5
        assert config.min_confidence == 0.0
        assert config.max_confidence == 1.0
        assert config.success_boost > 0
        assert config.failure_penalty > 0

    def test_custom_config(self):
        """Should accept custom settings."""
        config = ConfidenceConfig(
            initial_confidence=0.3,
            success_boost=0.15,
        )

        assert config.initial_confidence == 0.3
        assert config.success_boost == 0.15


class TestOutcomeType:
    """Test OutcomeType enum."""

    def test_outcome_types_exist(self):
        """Should have all outcome types."""
        assert OutcomeType.SUCCESS
        assert OutcomeType.FAILURE
        assert OutcomeType.PARTIAL
        assert OutcomeType.UNKNOWN


class TestActionOutcome:
    """Test ActionOutcome dataclass."""

    def test_create_outcome(self):
        """Should create action outcome."""
        outcome = ActionOutcome(
            action_type="file_edit",
            outcome=OutcomeType.SUCCESS,
            context={"file": "test.py"},
        )

        assert outcome.action_type == "file_edit"
        assert outcome.outcome == OutcomeType.SUCCESS
        assert outcome.context["file"] == "test.py"

    def test_outcome_has_timestamp(self):
        """Should have timestamp."""
        outcome = ActionOutcome(
            action_type="file_edit",
            outcome=OutcomeType.SUCCESS,
        )

        assert outcome.timestamp is not None


class TestConfidenceScore:
    """Test ConfidenceScore dataclass."""

    def test_create_score(self):
        """Should create confidence score."""
        score = ConfidenceScore(
            action_type="file_edit",
            score=0.75,
            sample_count=10,
        )

        assert score.action_type == "file_edit"
        assert score.score == 0.75
        assert score.sample_count == 10


class TestConfidenceTracker:
    """Test ConfidenceTracker."""

    @pytest.fixture
    def tracker(self):
        """Create confidence tracker."""
        return ConfidenceTracker()

    def test_create_tracker(self, tracker):
        """Should create tracker."""
        assert tracker is not None

    def test_get_initial_confidence(self, tracker):
        """Should return initial confidence for unknown action."""
        score = tracker.get_confidence("new_action")

        assert score.score == 0.5  # default initial
        assert score.sample_count == 0

    def test_record_success_increases_confidence(self, tracker):
        """Success should increase confidence."""
        initial = tracker.get_confidence("file_edit")

        tracker.record_outcome(ActionOutcome(
            action_type="file_edit",
            outcome=OutcomeType.SUCCESS,
        ))

        updated = tracker.get_confidence("file_edit")

        assert updated.score > initial.score

    def test_record_failure_decreases_confidence(self, tracker):
        """Failure should decrease confidence."""
        # Start with some successes to have confidence to lose
        for _ in range(3):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        before = tracker.get_confidence("file_edit")

        tracker.record_outcome(ActionOutcome(
            action_type="file_edit",
            outcome=OutcomeType.FAILURE,
        ))

        after = tracker.get_confidence("file_edit")

        assert after.score < before.score

    def test_confidence_bounded(self, tracker):
        """Confidence should stay within bounds."""
        # Many successes
        for _ in range(100):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        score = tracker.get_confidence("file_edit")
        assert score.score <= 1.0

        # Many failures
        for _ in range(200):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.FAILURE,
            ))

        score = tracker.get_confidence("file_edit")
        assert score.score >= 0.0

    def test_sample_count_tracks_outcomes(self, tracker):
        """Should track number of outcomes."""
        for _ in range(5):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        score = tracker.get_confidence("file_edit")
        assert score.sample_count == 5

    def test_partial_success_moderate_impact(self, tracker):
        """Partial success should have moderate impact."""
        initial = tracker.get_confidence("complex_task")

        tracker.record_outcome(ActionOutcome(
            action_type="complex_task",
            outcome=OutcomeType.PARTIAL,
        ))

        updated = tracker.get_confidence("complex_task")

        # Should have small positive or neutral effect
        assert updated.score >= initial.score - 0.1


class TestConfidenceByDomain:
    """Test domain-specific confidence tracking."""

    @pytest.fixture
    def tracker(self):
        """Create confidence tracker."""
        return ConfidenceTracker()

    def test_separate_confidence_per_action_type(self, tracker):
        """Different actions should have independent confidence."""
        # High confidence for file_edit
        for _ in range(10):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        # Low confidence for git_commit
        for _ in range(10):
            tracker.record_outcome(ActionOutcome(
                action_type="git_commit",
                outcome=OutcomeType.FAILURE,
            ))

        file_score = tracker.get_confidence("file_edit")
        git_score = tracker.get_confidence("git_commit")

        assert file_score.score > git_score.score

    def test_list_tracked_actions(self, tracker):
        """Should list all tracked action types."""
        tracker.record_outcome(ActionOutcome(
            action_type="file_edit",
            outcome=OutcomeType.SUCCESS,
        ))
        tracker.record_outcome(ActionOutcome(
            action_type="git_commit",
            outcome=OutcomeType.SUCCESS,
        ))

        actions = tracker.list_action_types()

        assert "file_edit" in actions
        assert "git_commit" in actions


class TestConfidenceRecency:
    """Test recency-weighted confidence."""

    @pytest.fixture
    def tracker(self):
        """Create tracker with recency weighting."""
        config = ConfidenceConfig(use_recency_weighting=True)
        return ConfidenceTracker(config=config)

    def test_recent_outcomes_weighted_more(self, tracker):
        """Recent outcomes should have more weight."""
        # Old failures (simulated with explicit timestamps)
        old_time = datetime.now() - timedelta(days=30)
        for _ in range(5):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.FAILURE,
                timestamp=old_time,
            ))

        # Recent successes
        for _ in range(3):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        score = tracker.get_confidence("file_edit")

        # Recent successes should outweigh old failures
        assert score.score > 0.5


class TestConfidenceStats:
    """Test confidence statistics."""

    @pytest.fixture
    def tracker(self):
        """Create tracker with history."""
        config = ConfidenceConfig(track_history=True)
        return ConfidenceTracker(config=config)

    def test_get_stats(self, tracker):
        """Should return statistics for action type."""
        for _ in range(7):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))
        for _ in range(3):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.FAILURE,
            ))

        stats = tracker.get_stats("file_edit")

        assert stats["success_count"] == 7
        assert stats["failure_count"] == 3
        assert stats["total_count"] == 10
        assert stats["success_rate"] == 0.7

    def test_get_all_scores(self, tracker):
        """Should return all confidence scores."""
        tracker.record_outcome(ActionOutcome(
            action_type="file_edit",
            outcome=OutcomeType.SUCCESS,
        ))
        tracker.record_outcome(ActionOutcome(
            action_type="git_commit",
            outcome=OutcomeType.FAILURE,
        ))

        scores = tracker.get_all_scores()

        assert len(scores) == 2
        assert any(s.action_type == "file_edit" for s in scores)
        assert any(s.action_type == "git_commit" for s in scores)
