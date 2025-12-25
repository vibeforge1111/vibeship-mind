"""
Feedback loop system for Mind v3.

Captures user feedback on Mind's actions and uses it to:
- Adjust confidence levels
- Learn from corrections
- Improve future suggestions

This is the primary way Mind learns user preferences.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .confidence import ConfidenceTracker

from .confidence import ActionOutcome, OutcomeType


class FeedbackType(str, Enum):
    """Types of user feedback."""

    APPROVE = "approve"      # User approved the action
    REJECT = "reject"        # User rejected the action
    CORRECT = "correct"      # User provided a correction
    IGNORE = "ignore"        # User ignored (no signal)


@dataclass
class UserFeedback:
    """User feedback on an action."""

    action_type: str
    feedback_type: FeedbackType
    timestamp: datetime = field(default_factory=datetime.now)
    comment: str = ""
    correction: str = ""
    context: dict = field(default_factory=dict)


@dataclass
class FeedbackEffect:
    """Effect of applying feedback."""

    applied: bool
    old_confidence: float
    new_confidence: float
    confidence_change: float
    message: str = ""


@dataclass
class FeedbackConfig:
    """Configuration for feedback loop."""

    # Confidence adjustments
    approval_boost: float = 0.15
    rejection_penalty: float = 0.2
    correction_penalty: float = 0.1  # Corrections are softer than rejection

    # History tracking
    track_history: bool = True
    max_history_per_action: int = 100

    # Learning
    learn_from_corrections: bool = True


class FeedbackLoop:
    """
    Manages the feedback loop between user and Mind.

    Records feedback, adjusts confidence, and tracks patterns
    for continuous improvement.
    """

    def __init__(
        self,
        config: FeedbackConfig | None = None,
        confidence_tracker: "ConfidenceTracker | None" = None,
    ):
        """
        Initialize feedback loop.

        Args:
            config: Feedback configuration
            confidence_tracker: Confidence tracking instance
        """
        self.config = config or FeedbackConfig()
        self._tracker = confidence_tracker
        self._history: dict[str, list[UserFeedback]] = defaultdict(list)
        self._corrections: dict[str, list[UserFeedback]] = defaultdict(list)

    def record_feedback(self, feedback: UserFeedback) -> FeedbackEffect:
        """
        Record user feedback and apply its effects.

        Args:
            feedback: User feedback to record

        Returns:
            Effect of the feedback
        """
        action_type = feedback.action_type

        # Get current confidence
        if self._tracker:
            old_score = self._tracker.get_confidence(action_type)
            old_confidence = old_score.score
        else:
            old_confidence = 0.5

        # Track history
        if self.config.track_history:
            self._history[action_type].append(feedback)

            # Trim history if too long
            if len(self._history[action_type]) > self.config.max_history_per_action:
                self._history[action_type] = self._history[action_type][-self.config.max_history_per_action:]

        # Apply feedback effect
        if feedback.feedback_type == FeedbackType.APPROVE:
            self._apply_approval(feedback)
        elif feedback.feedback_type == FeedbackType.REJECT:
            self._apply_rejection(feedback)
        elif feedback.feedback_type == FeedbackType.CORRECT:
            self._apply_correction(feedback)
        # IGNORE does nothing

        # Get new confidence
        if self._tracker:
            new_score = self._tracker.get_confidence(action_type)
            new_confidence = new_score.score
        else:
            new_confidence = old_confidence

        return FeedbackEffect(
            applied=feedback.feedback_type != FeedbackType.IGNORE,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            confidence_change=new_confidence - old_confidence,
            message=self._get_effect_message(feedback.feedback_type),
        )

    def _apply_approval(self, feedback: UserFeedback) -> None:
        """Apply approval feedback."""
        if self._tracker:
            self._tracker.record_outcome(ActionOutcome(
                action_type=feedback.action_type,
                outcome=OutcomeType.SUCCESS,
                context={"source": "user_feedback", "type": "approval"},
            ))

    def _apply_rejection(self, feedback: UserFeedback) -> None:
        """Apply rejection feedback."""
        if self._tracker:
            self._tracker.record_outcome(ActionOutcome(
                action_type=feedback.action_type,
                outcome=OutcomeType.FAILURE,
                context={"source": "user_feedback", "type": "rejection"},
            ))

    def _apply_correction(self, feedback: UserFeedback) -> None:
        """Apply correction feedback."""
        # Store correction for learning
        self._corrections[feedback.action_type].append(feedback)

        # Corrections have a smaller penalty than rejections
        if self._tracker:
            self._tracker.record_outcome(ActionOutcome(
                action_type=feedback.action_type,
                outcome=OutcomeType.PARTIAL,
                context={
                    "source": "user_feedback",
                    "type": "correction",
                    "correction": feedback.correction,
                },
            ))

    def _get_effect_message(self, feedback_type: FeedbackType) -> str:
        """Get message describing feedback effect."""
        messages = {
            FeedbackType.APPROVE: "Confidence increased from approval",
            FeedbackType.REJECT: "Confidence decreased from rejection",
            FeedbackType.CORRECT: "Correction recorded for learning",
            FeedbackType.IGNORE: "No effect from ignore",
        }
        return messages.get(feedback_type, "Feedback recorded")

    def get_history(self, action_type: str) -> list[UserFeedback]:
        """
        Get feedback history for an action type.

        Args:
            action_type: Type of action

        Returns:
            List of feedback entries
        """
        return list(self._history.get(action_type, []))

    def get_corrections(self, action_type: str) -> list[UserFeedback]:
        """
        Get corrections for an action type.

        Args:
            action_type: Type of action

        Returns:
            List of correction feedback entries
        """
        return list(self._corrections.get(action_type, []))

    def get_stats(self, action_type: str) -> dict:
        """
        Get feedback statistics for an action type.

        Args:
            action_type: Type of action

        Returns:
            Statistics dictionary
        """
        history = self._history.get(action_type, [])

        approval_count = sum(
            1 for f in history if f.feedback_type == FeedbackType.APPROVE
        )
        rejection_count = sum(
            1 for f in history if f.feedback_type == FeedbackType.REJECT
        )
        correction_count = sum(
            1 for f in history if f.feedback_type == FeedbackType.CORRECT
        )
        ignore_count = sum(
            1 for f in history if f.feedback_type == FeedbackType.IGNORE
        )

        total = len(history)
        non_ignore = approval_count + rejection_count + correction_count

        return {
            "approval_count": approval_count,
            "rejection_count": rejection_count,
            "correction_count": correction_count,
            "ignore_count": ignore_count,
            "total_count": total,
            "approval_rate": approval_count / non_ignore if non_ignore > 0 else 0.0,
            "rejection_rate": rejection_count / non_ignore if non_ignore > 0 else 0.0,
        }

    def get_correction_patterns(self, action_type: str) -> list[str]:
        """
        Extract patterns from corrections.

        Args:
            action_type: Type of action

        Returns:
            List of correction patterns/suggestions
        """
        corrections = self._corrections.get(action_type, [])

        # Extract unique corrections
        patterns = []
        seen = set()

        for feedback in corrections:
            if feedback.correction and feedback.correction not in seen:
                patterns.append(feedback.correction)
                seen.add(feedback.correction)

        return patterns

    def get_all_stats(self) -> dict:
        """
        Get statistics for all tracked actions.

        Returns:
            Dictionary mapping action types to stats
        """
        return {
            action_type: self.get_stats(action_type)
            for action_type in self._history.keys()
        }

    def clear_history(self, action_type: str | None = None) -> None:
        """
        Clear feedback history.

        Args:
            action_type: Specific action to clear, or None for all
        """
        if action_type:
            self._history.pop(action_type, None)
            self._corrections.pop(action_type, None)
        else:
            self._history.clear()
            self._corrections.clear()
