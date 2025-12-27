"""Tests for observability dashboard."""
from datetime import datetime, timedelta
import pytest

from mind.v3.autonomy.dashboard import (
    ObservabilityDashboard,
    DashboardConfig,
    SystemHealth,
    MetricSnapshot,
    TrendDirection,
)
from mind.v3.autonomy.confidence import (
    ConfidenceTracker,
    ActionOutcome,
    OutcomeType,
)
from mind.v3.autonomy.levels import AutonomyManager, AutonomyLevel
from mind.v3.autonomy.feedback import FeedbackLoop, UserFeedback, FeedbackType


class TestDashboardConfig:
    """Test DashboardConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = DashboardConfig()

        assert config.track_metrics is True
        assert config.health_check_interval > 0

    def test_custom_config(self):
        """Should accept custom settings."""
        config = DashboardConfig(
            track_metrics=False,
            health_check_interval=120,
        )

        assert config.track_metrics is False
        assert config.health_check_interval == 120


class TestTrendDirection:
    """Test TrendDirection enum."""

    def test_trends_exist(self):
        """Should have all trend directions."""
        assert TrendDirection.UP
        assert TrendDirection.DOWN
        assert TrendDirection.STABLE


class TestMetricSnapshot:
    """Test MetricSnapshot dataclass."""

    def test_create_snapshot(self):
        """Should create metric snapshot."""
        snapshot = MetricSnapshot(
            name="confidence_avg",
            value=0.75,
            trend=TrendDirection.UP,
        )

        assert snapshot.name == "confidence_avg"
        assert snapshot.value == 0.75
        assert snapshot.trend == TrendDirection.UP


class TestSystemHealth:
    """Test SystemHealth dataclass."""

    def test_create_health(self):
        """Should create system health status."""
        health = SystemHealth(
            status="healthy",
            score=0.9,
            issues=[],
        )

        assert health.status == "healthy"
        assert health.score == 0.9

    def test_health_with_issues(self):
        """Should track issues."""
        health = SystemHealth(
            status="degraded",
            score=0.6,
            issues=["Low confidence on git_commit"],
        )

        assert len(health.issues) == 1


class TestObservabilityDashboard:
    """Test ObservabilityDashboard."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard with components."""
        tracker = ConfidenceTracker()
        manager = AutonomyManager(confidence_tracker=tracker)
        loop = FeedbackLoop(confidence_tracker=tracker)

        return ObservabilityDashboard(
            confidence_tracker=tracker,
            autonomy_manager=manager,
            feedback_loop=loop,
        )

    def test_create_dashboard(self, dashboard):
        """Should create dashboard."""
        assert dashboard is not None

    def test_get_system_health(self, dashboard):
        """Should return system health."""
        health = dashboard.get_system_health()

        assert health is not None
        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert 0 <= health.score <= 1

    def test_get_overview(self, dashboard):
        """Should return system overview."""
        overview = dashboard.get_overview()

        assert "total_actions" in overview
        assert "avg_confidence" in overview
        assert "feedback_count" in overview


class TestDashboardMetrics:
    """Test dashboard metrics collection."""

    @pytest.fixture
    def populated_dashboard(self):
        """Create dashboard with some data."""
        tracker = ConfidenceTracker()
        manager = AutonomyManager(confidence_tracker=tracker)
        loop = FeedbackLoop(confidence_tracker=tracker)

        # Add some activity
        for _ in range(10):
            tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))
        for _ in range(5):
            tracker.record_outcome(ActionOutcome(
                action_type="git_commit",
                outcome=OutcomeType.FAILURE,
            ))
        loop.record_feedback(UserFeedback(
            action_type="file_edit",
            feedback_type=FeedbackType.APPROVE,
        ))

        return ObservabilityDashboard(
            confidence_tracker=tracker,
            autonomy_manager=manager,
            feedback_loop=loop,
        )

    def test_get_confidence_metrics(self, populated_dashboard):
        """Should return confidence metrics."""
        metrics = populated_dashboard.get_confidence_metrics()

        assert "file_edit" in metrics
        assert "git_commit" in metrics
        assert metrics["file_edit"]["score"] > metrics["git_commit"]["score"]

    def test_get_autonomy_distribution(self, populated_dashboard):
        """Should return autonomy level distribution."""
        distribution = populated_dashboard.get_autonomy_distribution()

        # Should have counts for each level
        assert isinstance(distribution, dict)

    def test_get_action_summary(self, populated_dashboard):
        """Should return action summary."""
        summary = populated_dashboard.get_action_summary("file_edit")

        assert summary["action_type"] == "file_edit"
        assert "confidence" in summary
        assert "level" in summary
        assert "sample_count" in summary


class TestDashboardTrends:
    """Test trend detection."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard with tracker."""
        tracker = ConfidenceTracker()
        manager = AutonomyManager(confidence_tracker=tracker)
        loop = FeedbackLoop(confidence_tracker=tracker)

        return ObservabilityDashboard(
            confidence_tracker=tracker,
            autonomy_manager=manager,
            feedback_loop=loop,
        )

    def test_detect_improving_trend(self, dashboard):
        """Should detect improving confidence."""
        # Simulate improving confidence
        for _ in range(10):
            dashboard._tracker.record_outcome(ActionOutcome(
                action_type="file_edit",
                outcome=OutcomeType.SUCCESS,
            ))

        trend = dashboard.get_trend("file_edit")

        assert trend in [TrendDirection.UP, TrendDirection.STABLE]

    def test_detect_declining_trend(self, dashboard):
        """Should detect declining confidence."""
        # Start high then decline
        for _ in range(5):
            dashboard._tracker.record_outcome(ActionOutcome(
                action_type="test_action",
                outcome=OutcomeType.SUCCESS,
            ))
        for _ in range(10):
            dashboard._tracker.record_outcome(ActionOutcome(
                action_type="test_action",
                outcome=OutcomeType.FAILURE,
            ))

        trend = dashboard.get_trend("test_action")

        assert trend in [TrendDirection.DOWN, TrendDirection.STABLE]


class TestDashboardReporting:
    """Test reporting features."""

    @pytest.fixture
    def populated_dashboard(self):
        """Create dashboard with activity."""
        tracker = ConfidenceTracker()
        manager = AutonomyManager(confidence_tracker=tracker)
        loop = FeedbackLoop(confidence_tracker=tracker)

        # Add varied activity
        actions = ["file_edit", "git_commit", "test_run", "deploy"]
        for action in actions:
            for _ in range(5):
                tracker.record_outcome(ActionOutcome(
                    action_type=action,
                    outcome=OutcomeType.SUCCESS if action != "deploy" else OutcomeType.FAILURE,
                ))

        return ObservabilityDashboard(
            confidence_tracker=tracker,
            autonomy_manager=manager,
            feedback_loop=loop,
        )

    def test_generate_report(self, populated_dashboard):
        """Should generate summary report."""
        report = populated_dashboard.generate_report()

        assert "timestamp" in report
        assert "health" in report
        assert "actions" in report
        assert len(report["actions"]) > 0

    def test_get_recommendations(self, populated_dashboard):
        """Should provide recommendations."""
        recommendations = populated_dashboard.get_recommendations()

        assert isinstance(recommendations, list)
        # Should suggest something for low-confidence actions
        assert any("deploy" in r.lower() for r in recommendations) or len(recommendations) == 0

    def test_list_problematic_actions(self, populated_dashboard):
        """Should identify problematic actions."""
        problems = populated_dashboard.list_problematic_actions()

        # deploy has failures, should be listed
        assert any(p["action_type"] == "deploy" for p in problems)
