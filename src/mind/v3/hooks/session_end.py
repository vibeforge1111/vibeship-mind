"""
SessionEnd hook for Claude Code integration.

Handles session cleanup:
- Consolidates session memories
- Generates session summary
- Persists important learnings
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..memory.consolidation import MemoryConsolidator, ConsolidationConfig
from ..memory.working_memory import MemoryItem, MemoryType

if TYPE_CHECKING:
    from ..graph.store import GraphStore


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
        graph_store: GraphStore | None = None,
    ):
        """
        Initialize hook.

        Args:
            project_path: Path to project directory
            config: Hook configuration
            graph_store: Optional graph store for persisting patterns
        """
        self.project_path = project_path
        self.config = config or SessionEndConfig()
        self._graph_store = graph_store

        # Session events
        self._events: list[dict[str, Any]] = []

        # Memory consolidator (with min_occurrences=2 for easier pattern detection)
        self._consolidator = MemoryConsolidator(ConsolidationConfig(min_occurrences=2))

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
        Consolidate similar events into memories using MemoryConsolidator.

        Returns:
            Number of patterns created
        """
        # Convert events to MemoryItems
        memory_items = self._events_to_memory_items()

        if not memory_items:
            return 0

        # Run consolidation
        patterns = self._consolidator.consolidate(memory_items)

        # Store patterns in graph store if available
        if self._graph_store and patterns:
            for pattern in patterns:
                self._graph_store.add_pattern({
                    "description": pattern.description,
                    "pattern_type": pattern.metadata.get("memory_type", "unknown"),
                    "confidence": pattern.confidence,
                    "evidence_count": pattern.occurrences,
                })

        return len(patterns)

    def _events_to_memory_items(self) -> list[MemoryItem]:
        """
        Convert session events to MemoryItems for consolidation.

        Returns:
            List of MemoryItem objects
        """
        items = []
        for i, event in enumerate(self._events):
            description = event.get("description", "")

            # Infer memory type from description keywords
            memory_type = self._infer_memory_type(description)

            item = MemoryItem(
                id=f"event-{i}-{uuid.uuid4().hex[:8]}",
                content=description,
                memory_type=memory_type,
                importance=0.5,  # Default importance
                created_at=datetime.now(),
            )
            items.append(item)

        return items

    def _infer_memory_type(self, description: str) -> MemoryType:
        """
        Infer the memory type from event description.

        Args:
            description: Event description text

        Returns:
            Inferred MemoryType
        """
        desc_lower = description.lower()

        # Decision keywords
        if any(kw in desc_lower for kw in ["decided", "chose", "using", "selected"]):
            return MemoryType.DECISION

        # Learning keywords
        if any(kw in desc_lower for kw in ["learned", "discovered", "realized", "found out"]):
            return MemoryType.LEARNING

        # Default to EVENT
        return MemoryType.EVENT

    def get_events(self) -> list[dict]:
        """
        Get all session events.

        Returns:
            List of event dictionaries
        """
        return list(self._events)
