"""
Autonomy levels system for Mind v3.

Defines progressive autonomy levels that Mind can operate at,
based on confidence tracking and user trust.

Levels (1-5):
1. RECORD_ONLY: Just observe and capture
2. SUGGEST: Propose actions based on precedent
3. ASK_PERMISSION: Propose with confidence, ask before acting
4. ACT_NOTIFY: Act automatically, inform user after
5. SILENT: Handle automatically, log only
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .confidence import ConfidenceTracker


class AutonomyLevel(IntEnum):
    """Progressive autonomy levels."""

    RECORD_ONLY = 1      # Observe and capture only
    SUGGEST = 2          # Propose based on precedent
    ASK_PERMISSION = 3   # Propose with confidence, ask first
    ACT_NOTIFY = 4       # Act automatically, notify user
    SILENT = 5           # Handle automatically, log only


# Level descriptions
LEVEL_DESCRIPTIONS = {
    AutonomyLevel.RECORD_ONLY: "Record Only - Observe and capture actions without suggesting",
    AutonomyLevel.SUGGEST: "Suggest - Propose actions based on past patterns and precedent",
    AutonomyLevel.ASK_PERMISSION: "Ask Permission - Propose with confidence, await approval",
    AutonomyLevel.ACT_NOTIFY: "Act + Notify - Execute automatically, inform user after",
    AutonomyLevel.SILENT: "Silent - Handle automatically with logging only",
}

# Level guidance
LEVEL_GUIDANCE = {
    AutonomyLevel.RECORD_ONLY: "Mind will only observe and record your actions for learning.",
    AutonomyLevel.SUGGEST: "Mind will suggest actions based on patterns it has learned.",
    AutonomyLevel.ASK_PERMISSION: "Mind will propose confident actions and wait for your approval.",
    AutonomyLevel.ACT_NOTIFY: "Mind will automatically take actions and notify you of what it did.",
    AutonomyLevel.SILENT: "Mind will handle actions silently, only logging for audit purposes.",
}


@dataclass
class AutonomyConfig:
    """Configuration for autonomy management."""

    # Default level for unknown actions
    default_level: AutonomyLevel = AutonomyLevel.SUGGEST

    # Maximum level allowed (global cap)
    max_level: AutonomyLevel = AutonomyLevel.ACT_NOTIFY

    # Confidence thresholds for each level
    level_thresholds: dict[AutonomyLevel, float] = field(default_factory=lambda: {
        AutonomyLevel.RECORD_ONLY: 0.0,    # Always available
        AutonomyLevel.SUGGEST: 0.2,         # Low confidence needed
        AutonomyLevel.ASK_PERMISSION: 0.5,  # Medium confidence
        AutonomyLevel.ACT_NOTIFY: 0.8,      # High confidence
        AutonomyLevel.SILENT: 0.95,         # Very high confidence
    })


@dataclass
class ActionPolicy:
    """Policy for a specific action type."""

    action_type: str
    current_level: AutonomyLevel
    max_allowed_level: AutonomyLevel
    confidence: float
    sample_count: int = 0

    def allows(self, level: AutonomyLevel) -> bool:
        """
        Check if action is allowed at the given level.

        Args:
            level: Level to check

        Returns:
            True if action can be performed at this level
        """
        return level.value <= self.current_level.value


class AutonomyManager:
    """
    Manages autonomy levels for different action types.

    Maps confidence scores to autonomy levels and enforces
    maximum level constraints.
    """

    def __init__(
        self,
        config: AutonomyConfig | None = None,
        confidence_tracker: "ConfidenceTracker | None" = None,
    ):
        """
        Initialize autonomy manager.

        Args:
            config: Autonomy configuration
            confidence_tracker: Confidence tracking instance
        """
        self.config = config or AutonomyConfig()
        self._tracker = confidence_tracker
        self._action_max_levels: dict[str, AutonomyLevel] = {}
        self._level_overrides: dict[str, AutonomyLevel] = {}

    def get_level(self, action_type: str) -> AutonomyLevel:
        """
        Get current autonomy level for an action type.

        Args:
            action_type: Type of action

        Returns:
            Current autonomy level
        """
        # Check for manual override
        if action_type in self._level_overrides:
            return self._level_overrides[action_type]

        # Get confidence if tracker available
        if self._tracker:
            score = self._tracker.get_confidence(action_type)
            if score.sample_count == 0:
                # No data yet, use default level
                level = self.config.default_level
            else:
                # Determine level based on confidence
                level = self._confidence_to_level(score.score)
        else:
            # No tracker, use default level
            level = self.config.default_level

        # Apply action-specific max
        action_max = self._action_max_levels.get(action_type, self.config.max_level)

        # Apply global max
        final_level = min(level, action_max, self.config.max_level, key=lambda x: x.value)

        return final_level

    def _confidence_to_level(self, confidence: float) -> AutonomyLevel:
        """
        Convert confidence score to autonomy level.

        Args:
            confidence: Confidence score (0-1)

        Returns:
            Corresponding autonomy level
        """
        # Check thresholds from highest to lowest
        sorted_levels = sorted(
            self.config.level_thresholds.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        for level, threshold in sorted_levels:
            if confidence >= threshold:
                return level

        return AutonomyLevel.RECORD_ONLY

    def get_policy(self, action_type: str) -> ActionPolicy:
        """
        Get full policy for an action type.

        Args:
            action_type: Type of action

        Returns:
            Action policy with level and constraints
        """
        level = self.get_level(action_type)
        action_max = self._action_max_levels.get(action_type, self.config.max_level)

        if self._tracker:
            score = self._tracker.get_confidence(action_type)
            confidence = score.score
            sample_count = score.sample_count
        else:
            confidence = 0.5
            sample_count = 0

        return ActionPolicy(
            action_type=action_type,
            current_level=level,
            max_allowed_level=min(action_max, self.config.max_level, key=lambda x: x.value),
            confidence=confidence,
            sample_count=sample_count,
        )

    def set_action_max_level(self, action_type: str, max_level: AutonomyLevel) -> None:
        """
        Set maximum autonomy level for a specific action.

        Args:
            action_type: Type of action
            max_level: Maximum level allowed
        """
        self._action_max_levels[action_type] = max_level

    def override_level(self, action_type: str, level: AutonomyLevel) -> None:
        """
        Manually override level for an action type.

        Args:
            action_type: Type of action
            level: Level to set
        """
        self._level_overrides[action_type] = level

    def clear_override(self, action_type: str) -> None:
        """
        Clear manual level override.

        Args:
            action_type: Type of action
        """
        self._level_overrides.pop(action_type, None)

    def get_level_description(self, level: AutonomyLevel) -> str:
        """
        Get description for an autonomy level.

        Args:
            level: Autonomy level

        Returns:
            Human-readable description
        """
        return LEVEL_DESCRIPTIONS.get(level, "Unknown level")

    def get_level_guidance(self, level: AutonomyLevel) -> str:
        """
        Get guidance for an autonomy level.

        Args:
            level: Autonomy level

        Returns:
            Guidance on what happens at this level
        """
        return LEVEL_GUIDANCE.get(level, "No guidance available")

    def get_summary(self) -> dict:
        """
        Get summary of all tracked actions and their levels.

        Returns:
            Dictionary mapping action types to their status
        """
        summary = {}

        if self._tracker:
            for score in self._tracker.get_all_scores():
                action_type = score.action_type
                level = self.get_level(action_type)

                summary[action_type] = {
                    "level": level.name,
                    "level_value": level.value,
                    "confidence": score.score,
                    "sample_count": score.sample_count,
                    "description": self.get_level_description(level),
                }

        return summary

    def list_actions_at_level(self, level: AutonomyLevel) -> list[str]:
        """
        List all actions at or above a given level.

        Args:
            level: Minimum level to include

        Returns:
            List of action type names
        """
        actions = []

        if self._tracker:
            for score in self._tracker.get_all_scores():
                action_level = self.get_level(score.action_type)
                if action_level.value >= level.value:
                    actions.append(score.action_type)

        return actions
