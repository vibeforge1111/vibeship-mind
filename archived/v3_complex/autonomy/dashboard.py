"""
Observability dashboard for Mind v3.

Provides unified visibility into the autonomy system:
- System health monitoring
- Confidence metrics and trends
- Autonomy level distribution
- Recommendations for improvement
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .confidence import ConfidenceTracker
    from .levels import AutonomyManager
    from .feedback import FeedbackLoop


class TrendDirection(str, Enum):
    """Direction of metric trend."""

    UP = "up"           # Improving
    DOWN = "down"       # Declining
    STABLE = "stable"   # No significant change


@dataclass
class MetricSnapshot:
    """Snapshot of a metric value."""

    name: str
    value: float
    trend: TrendDirection = TrendDirection.STABLE
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class SystemHealth:
    """System health status."""

    status: str  # healthy, degraded, unhealthy
    score: float  # 0-1 health score
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DashboardConfig:
    """Configuration for observability dashboard."""

    # Metrics collection
    track_metrics: bool = True
    metrics_window_hours: int = 24

    # Health checks
    health_check_interval: int = 60  # seconds

    # Thresholds
    low_confidence_threshold: float = 0.3
    problematic_failure_rate: float = 0.5


class ObservabilityDashboard:
    """
    Unified observability for the autonomy system.

    Aggregates data from confidence tracking, autonomy levels,
    and feedback to provide system-wide visibility.
    """

    def __init__(
        self,
        confidence_tracker: "ConfidenceTracker | None" = None,
        autonomy_manager: "AutonomyManager | None" = None,
        feedback_loop: "FeedbackLoop | None" = None,
        config: DashboardConfig | None = None,
    ):
        """
        Initialize dashboard.

        Args:
            confidence_tracker: Confidence tracking instance
            autonomy_manager: Autonomy management instance
            feedback_loop: Feedback loop instance
            config: Dashboard configuration
        """
        self.config = config or DashboardConfig()
        self._tracker = confidence_tracker
        self._manager = autonomy_manager
        self._feedback = feedback_loop
        self._metric_history: list[MetricSnapshot] = []

    def get_system_health(self) -> SystemHealth:
        """
        Get overall system health status.

        Returns:
            System health with status and score
        """
        issues = []
        score = 1.0

        # Check confidence levels
        if self._tracker:
            scores = self._tracker.get_all_scores()
            for s in scores:
                if s.score < self.config.low_confidence_threshold:
                    issues.append(f"Low confidence on {s.action_type} ({s.score:.2f})")
                    score -= 0.1

        # Check for consistent failures
        if self._feedback:
            all_stats = self._feedback.get_all_stats()
            for action_type, stats in all_stats.items():
                if stats["total_count"] > 0:
                    failure_rate = stats["rejection_count"] / stats["total_count"]
                    if failure_rate > self.config.problematic_failure_rate:
                        issues.append(f"High rejection rate on {action_type}")
                        score -= 0.15

        # Clamp score
        score = max(0.0, min(1.0, score))

        # Determine status
        if score >= 0.8:
            status = "healthy"
        elif score >= 0.5:
            status = "degraded"
        else:
            status = "unhealthy"

        return SystemHealth(
            status=status,
            score=score,
            issues=issues,
            recommendations=self._generate_health_recommendations(issues),
        )

    def _generate_health_recommendations(self, issues: list[str]) -> list[str]:
        """Generate recommendations based on issues."""
        recommendations = []

        for issue in issues:
            if "Low confidence" in issue:
                recommendations.append("Consider providing more positive feedback for reliable actions")
            elif "High rejection" in issue:
                recommendations.append("Review and adjust autonomy levels for problematic actions")

        return recommendations

    def get_overview(self) -> dict:
        """
        Get high-level system overview.

        Returns:
            Overview dictionary with key metrics
        """
        total_actions = 0
        avg_confidence = 0.0
        feedback_count = 0

        if self._tracker:
            scores = self._tracker.get_all_scores()
            total_actions = len(scores)
            if scores:
                avg_confidence = sum(s.score for s in scores) / len(scores)

        if self._feedback:
            all_stats = self._feedback.get_all_stats()
            feedback_count = sum(s["total_count"] for s in all_stats.values())

        return {
            "total_actions": total_actions,
            "avg_confidence": avg_confidence,
            "feedback_count": feedback_count,
            "health": self.get_system_health().status,
            "timestamp": datetime.now().isoformat(),
        }

    def get_confidence_metrics(self) -> dict:
        """
        Get confidence metrics for all actions.

        Returns:
            Dictionary mapping action types to metrics
        """
        metrics = {}

        if self._tracker:
            for score in self._tracker.get_all_scores():
                metrics[score.action_type] = {
                    "score": score.score,
                    "sample_count": score.sample_count,
                    "trend": self.get_trend(score.action_type).value,
                }

        return metrics

    def get_autonomy_distribution(self) -> dict:
        """
        Get distribution of actions across autonomy levels.

        Returns:
            Dictionary mapping level names to counts
        """
        from .levels import AutonomyLevel

        distribution = {level.name: 0 for level in AutonomyLevel}

        if self._manager and self._tracker:
            for score in self._tracker.get_all_scores():
                level = self._manager.get_level(score.action_type)
                distribution[level.name] += 1

        return distribution

    def get_action_summary(self, action_type: str) -> dict:
        """
        Get detailed summary for a specific action.

        Args:
            action_type: Type of action

        Returns:
            Summary dictionary
        """
        summary = {
            "action_type": action_type,
            "confidence": 0.5,
            "level": "SUGGEST",
            "sample_count": 0,
            "trend": TrendDirection.STABLE.value,
            "feedback_stats": {},
        }

        if self._tracker:
            score = self._tracker.get_confidence(action_type)
            summary["confidence"] = score.score
            summary["sample_count"] = score.sample_count
            summary["trend"] = self.get_trend(action_type).value

        if self._manager:
            level = self._manager.get_level(action_type)
            summary["level"] = level.name

        if self._feedback:
            summary["feedback_stats"] = self._feedback.get_stats(action_type)

        return summary

    def get_trend(self, action_type: str) -> TrendDirection:
        """
        Determine trend direction for an action.

        Args:
            action_type: Type of action

        Returns:
            Trend direction
        """
        if not self._tracker:
            return TrendDirection.STABLE

        score = self._tracker.get_confidence(action_type)

        # Simple trend detection based on recent activity
        # In a full implementation, this would track history
        if score.sample_count < 3:
            return TrendDirection.STABLE

        # Use confidence level as proxy for trend
        if score.score > 0.7:
            return TrendDirection.UP
        elif score.score < 0.3:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STABLE

    def generate_report(self) -> dict:
        """
        Generate comprehensive system report.

        Returns:
            Report dictionary
        """
        health = self.get_system_health()

        actions = []
        if self._tracker:
            for score in self._tracker.get_all_scores():
                actions.append(self.get_action_summary(score.action_type))

        return {
            "timestamp": datetime.now().isoformat(),
            "health": {
                "status": health.status,
                "score": health.score,
                "issues": health.issues,
            },
            "overview": self.get_overview(),
            "actions": actions,
            "distribution": self.get_autonomy_distribution(),
            "recommendations": self.get_recommendations(),
        }

    def get_recommendations(self) -> list[str]:
        """
        Get actionable recommendations.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if self._tracker:
            for score in self._tracker.get_all_scores():
                if score.score < self.config.low_confidence_threshold:
                    recommendations.append(
                        f"Consider manual review of '{score.action_type}' - confidence is low ({score.score:.2f})"
                    )

        if self._feedback:
            all_stats = self._feedback.get_all_stats()
            for action_type, stats in all_stats.items():
                if stats["total_count"] >= 5 and stats["rejection_rate"] > 0.5:
                    recommendations.append(
                        f"High rejection rate for '{action_type}' - consider reducing autonomy level"
                    )

        return recommendations

    def list_problematic_actions(self) -> list[dict]:
        """
        List actions with problems.

        Returns:
            List of problematic action summaries
        """
        problems = []

        if self._tracker:
            for score in self._tracker.get_all_scores():
                issues = []

                if score.score < self.config.low_confidence_threshold:
                    issues.append("low_confidence")

                if self._feedback:
                    stats = self._feedback.get_stats(score.action_type)
                    if stats["total_count"] > 0:
                        rejection_rate = stats["rejection_count"] / stats["total_count"]
                        if rejection_rate > self.config.problematic_failure_rate:
                            issues.append("high_rejection_rate")

                if issues:
                    problems.append({
                        "action_type": score.action_type,
                        "confidence": score.score,
                        "issues": issues,
                    })

        return problems
