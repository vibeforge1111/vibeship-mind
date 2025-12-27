"""Unified autonomy tracking for v3."""
from __future__ import annotations

from .confidence import ConfidenceTracker, ActionOutcome, OutcomeType
from .levels import AutonomyManager, AutonomyConfig, AutonomyLevel
from .feedback import FeedbackLoop


class AutonomyTracker:
    """
    Unified autonomy tracking for v3.

    Brings together confidence tracking, autonomy levels, and feedback
    into a single interface for the bridge to use.
    """

    def __init__(self):
        """Initialize autonomy tracker with all subsystems."""
        self.confidence = ConfidenceTracker()
        self.levels = AutonomyManager(confidence_tracker=self.confidence)
        self.feedback = FeedbackLoop(confidence_tracker=self.confidence)

    def record_decision(self, action_type: str, success: bool) -> None:
        """
        Record a decision outcome.

        Args:
            action_type: Type of action (e.g., "file_edit", "git_commit")
            success: Whether the action was successful
        """
        outcome = ActionOutcome(
            action_type=action_type,
            outcome=OutcomeType.SUCCESS if success else OutcomeType.FAILURE,
        )
        self.confidence.record_outcome(outcome)

    def get_autonomy_level(self, action_type: str) -> AutonomyLevel:
        """
        Get current autonomy level for an action.

        Args:
            action_type: Type of action

        Returns:
            Current autonomy level for this action type
        """
        return self.levels.get_level(action_type)

    def get_summary(self) -> dict:
        """
        Get autonomy summary for all tracked actions.

        Returns:
            Dictionary with autonomy status for all tracked actions
        """
        return self.levels.get_summary()
