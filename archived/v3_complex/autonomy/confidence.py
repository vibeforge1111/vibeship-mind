"""
Confidence tracking system for Mind v3.

Tracks confidence levels for different action types based on outcomes.
Confidence determines what autonomy level Mind can operate at.

Key concepts:
- Action type: Category of action (file_edit, git_commit, etc.)
- Outcome: Success/failure of an action
- Confidence: Probability that similar actions will succeed
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class OutcomeType(str, Enum):
    """Types of action outcomes."""

    SUCCESS = "success"       # Action succeeded completely
    FAILURE = "failure"       # Action failed
    PARTIAL = "partial"       # Partial success
    UNKNOWN = "unknown"       # Outcome not determined


@dataclass
class ActionOutcome:
    """Record of an action outcome."""

    action_type: str
    outcome: OutcomeType
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict = field(default_factory=dict)
    details: str = ""


@dataclass
class ConfidenceScore:
    """Confidence score for an action type."""

    action_type: str
    score: float
    sample_count: int
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ConfidenceConfig:
    """Configuration for confidence tracking."""

    # Initial confidence for unknown actions
    initial_confidence: float = 0.5

    # Bounds
    min_confidence: float = 0.0
    max_confidence: float = 1.0

    # Adjustment amounts
    success_boost: float = 0.1
    failure_penalty: float = 0.15
    partial_boost: float = 0.03

    # Recency weighting
    use_recency_weighting: bool = False
    recency_half_life_days: float = 7.0

    # History tracking
    track_history: bool = False


class ConfidenceTracker:
    """
    Tracks confidence levels for different action types.

    Confidence is updated based on outcomes:
    - Success increases confidence
    - Failure decreases confidence
    - Partial success has moderate effect

    Optionally weights recent outcomes more heavily.
    """

    def __init__(self, config: ConfidenceConfig | None = None):
        """
        Initialize confidence tracker.

        Args:
            config: Confidence configuration
        """
        self.config = config or ConfidenceConfig()
        self._scores: dict[str, float] = {}
        self._counts: dict[str, int] = defaultdict(int)
        self._outcomes: dict[str, list[ActionOutcome]] = defaultdict(list)

    def get_confidence(self, action_type: str) -> ConfidenceScore:
        """
        Get current confidence score for an action type.

        Args:
            action_type: Type of action

        Returns:
            Current confidence score
        """
        if action_type not in self._scores:
            return ConfidenceScore(
                action_type=action_type,
                score=self.config.initial_confidence,
                sample_count=0,
            )

        if self.config.use_recency_weighting and self._outcomes[action_type]:
            # Recalculate with recency weighting
            score = self._calculate_recency_weighted_score(action_type)
        else:
            score = self._scores[action_type]

        return ConfidenceScore(
            action_type=action_type,
            score=score,
            sample_count=self._counts[action_type],
        )

    def record_outcome(self, outcome: ActionOutcome) -> None:
        """
        Record an action outcome and update confidence.

        Args:
            outcome: The action outcome to record
        """
        action_type = outcome.action_type

        # Store outcome if tracking history
        if self.config.track_history or self.config.use_recency_weighting:
            self._outcomes[action_type].append(outcome)

        # Increment count
        self._counts[action_type] += 1

        # Get current score (or initial)
        current = self._scores.get(action_type, self.config.initial_confidence)

        # Calculate adjustment
        if outcome.outcome == OutcomeType.SUCCESS:
            adjustment = self.config.success_boost
        elif outcome.outcome == OutcomeType.FAILURE:
            adjustment = -self.config.failure_penalty
        elif outcome.outcome == OutcomeType.PARTIAL:
            adjustment = self.config.partial_boost
        else:
            adjustment = 0.0

        # Apply adjustment with diminishing returns
        # Use logistic curve to make changes smaller near bounds
        new_score = current + adjustment * self._diminishing_factor(current, adjustment)

        # Clamp to bounds
        new_score = max(self.config.min_confidence, new_score)
        new_score = min(self.config.max_confidence, new_score)

        self._scores[action_type] = new_score

    def _diminishing_factor(self, current: float, adjustment: float) -> float:
        """
        Calculate diminishing returns factor.

        Makes it harder to reach extremes (0 or 1).
        """
        if adjustment > 0:
            # Positive adjustment: harder to increase near max
            return 1.0 - (current ** 2)
        else:
            # Negative adjustment: harder to decrease near min
            return current ** 0.5

    def _calculate_recency_weighted_score(self, action_type: str) -> float:
        """
        Calculate confidence with recency weighting.

        More recent outcomes have more influence.
        """
        outcomes = self._outcomes.get(action_type, [])
        if not outcomes:
            return self.config.initial_confidence

        now = datetime.now()
        half_life = timedelta(days=self.config.recency_half_life_days)

        weighted_sum = 0.0
        weight_total = 0.0

        for outcome in outcomes:
            # Calculate age in half-lives
            age = now - outcome.timestamp
            age_in_half_lives = age.total_seconds() / half_life.total_seconds()

            # Exponential decay weight
            weight = math.pow(0.5, age_in_half_lives)

            # Outcome value
            if outcome.outcome == OutcomeType.SUCCESS:
                value = 1.0
            elif outcome.outcome == OutcomeType.FAILURE:
                value = 0.0
            elif outcome.outcome == OutcomeType.PARTIAL:
                value = 0.5
            else:
                value = 0.5

            weighted_sum += value * weight
            weight_total += weight

        if weight_total == 0:
            return self.config.initial_confidence

        return weighted_sum / weight_total

    def list_action_types(self) -> list[str]:
        """
        List all tracked action types.

        Returns:
            List of action type names
        """
        return list(self._scores.keys())

    def get_stats(self, action_type: str) -> dict:
        """
        Get statistics for an action type.

        Args:
            action_type: Type of action

        Returns:
            Statistics dictionary
        """
        outcomes = self._outcomes.get(action_type, [])

        success_count = sum(
            1 for o in outcomes if o.outcome == OutcomeType.SUCCESS
        )
        failure_count = sum(
            1 for o in outcomes if o.outcome == OutcomeType.FAILURE
        )
        partial_count = sum(
            1 for o in outcomes if o.outcome == OutcomeType.PARTIAL
        )
        total = len(outcomes)

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "partial_count": partial_count,
            "total_count": total,
            "success_rate": success_count / total if total > 0 else 0.0,
            "current_score": self._scores.get(action_type, self.config.initial_confidence),
        }

    def get_all_scores(self) -> list[ConfidenceScore]:
        """
        Get all confidence scores.

        Returns:
            List of all confidence scores
        """
        return [
            self.get_confidence(action_type)
            for action_type in self._scores.keys()
        ]

    def reset(self, action_type: str | None = None) -> None:
        """
        Reset confidence tracking.

        Args:
            action_type: Specific action to reset, or None for all
        """
        if action_type:
            self._scores.pop(action_type, None)
            self._counts.pop(action_type, None)
            self._outcomes.pop(action_type, None)
        else:
            self._scores.clear()
            self._counts.clear()
            self._outcomes.clear()
