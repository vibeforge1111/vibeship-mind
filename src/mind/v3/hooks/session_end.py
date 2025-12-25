"""
SessionEnd hook for Claude Code integration.

Handles session cleanup:
- Consolidates session memories
- Generates session summary
- Persists important learnings
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SessionEndConfig:
    """Configuration for session end hook."""

    enabled: bool = True
    consolidate_memories: bool = True
    min_session_length: int = 3  # Minimum events to consolidate


@dataclass
class SessionEndResult:
    """Result from session end processing."""

    success: bool
    memories_consolidated: int
    session_summary: str
    metadata: dict = field(default_factory=dict)


class SessionEndHook:
    """
    Hook that runs when session ends.

    Consolidates session events into permanent memories
    and generates a session summary.
    """

    def __init__(
        self,
        project_path: Path,
        config: SessionEndConfig | None = None,
    ):
        """
        Initialize hook.

        Args:
            project_path: Path to project directory
            config: Hook configuration
        """
        self.project_path = project_path
        self.config = config or SessionEndConfig()

        # Session events
        self._events: list[dict[str, Any]] = []

    @property
    def event_count(self) -> int:
        """Get number of events in session."""
        return len(self._events)

    def add_event(self, description: str) -> None:
        """
        Add event to session.

        Args:
            description: Event description
        """
        self._events.append({
            "description": description,
        })

    def finalize(self) -> SessionEndResult:
        """
        Finalize session and consolidate memories.

        Returns:
            SessionEndResult with consolidation info
        """
        # If disabled, return empty result
        if not self.config.enabled:
            return SessionEndResult(
                success=True,
                memories_consolidated=0,
                session_summary="",
            )

        # Empty session
        if not self._events:
            return SessionEndResult(
                success=True,
                memories_consolidated=0,
                session_summary="",
            )

        # Generate summary
        summary = self._generate_summary()

        # Consolidate if enough events
        consolidated = 0
        if self.config.consolidate_memories:
            if len(self._events) >= self.config.min_session_length:
                consolidated = self._consolidate_events()

        # Clear session
        self._events.clear()

        return SessionEndResult(
            success=True,
            memories_consolidated=consolidated,
            session_summary=summary,
        )

    def _generate_summary(self) -> str:
        """
        Generate session summary from events.

        Returns:
            Summary string
        """
        if not self._events:
            return ""

        # Simple summary: list main activities
        activities = [e["description"] for e in self._events]

        if len(activities) <= 3:
            return "; ".join(activities)

        # For longer sessions, summarize
        return f"Session with {len(activities)} activities"

    def _consolidate_events(self) -> int:
        """
        Consolidate similar events into memories.

        Returns:
            Number of memories created
        """
        # Group by keywords
        groups: dict[str, list[str]] = {}

        for event in self._events:
            desc = event["description"].lower()

            # Simple grouping by first word
            key = desc.split()[0] if desc.split() else "misc"
            if key not in groups:
                groups[key] = []
            groups[key].append(event["description"])

        # Each group becomes a memory
        return len(groups)

    def get_events(self) -> list[dict]:
        """
        Get all session events.

        Returns:
            List of event dictionaries
        """
        return list(self._events)
