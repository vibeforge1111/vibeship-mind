"""
Transcript watcher for Mind v3.

Watches transcript events and automatically extracts learnings,
decisions, and entities to the context graph.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

from .events import Event, EventType, DecisionEvent
from .extractor import TranscriptExtractor

if TYPE_CHECKING:
    from ..graph.store import GraphStore


@dataclass
class WatcherConfig:
    """Configuration for transcript watcher."""

    enabled: bool = True
    extract_decisions: bool = True
    extract_entities: bool = True
    min_decision_confidence: float = 0.3


@dataclass
class WatcherStats:
    """Statistics from watcher processing."""

    turns_processed: int = 0
    events_extracted: int = 0
    decisions_stored: int = 0
    entities_stored: int = 0


class TranscriptWatcher:
    """
    Watches transcript events and stores extracted data to graph.

    Connects TranscriptExtractor to GraphStore for automatic
    capture of decisions, entities, and patterns.
    """

    def __init__(
        self,
        graph_store: "GraphStore | None" = None,
        config: WatcherConfig | None = None,
    ):
        """
        Initialize watcher.

        Args:
            graph_store: GraphStore for persistence
            config: Watcher configuration
        """
        self._graph_store = graph_store
        self.config = config or WatcherConfig()
        self._extractor = TranscriptExtractor()
        self._stats = WatcherStats()

        # Entity extractor for additional entity detection
        self._entity_extractor = None
        if self.config.extract_entities:
            try:
                from ..intelligence.extractors.entity import LocalEntityExtractor
                self._entity_extractor = LocalEntityExtractor()
            except Exception:
                logger.debug("LocalEntityExtractor init failed, entity extraction disabled", exc_info=True)

    def process_turn(self, turn: dict[str, Any]) -> list[Event]:
        """
        Process a single conversation turn.

        Args:
            turn: Conversation turn with 'role' and 'content'

        Returns:
            List of extracted events
        """
        if not self.config.enabled:
            return []

        events = self._extractor.extract_from_turn(turn)
        self._stats.turns_processed += 1
        self._stats.events_extracted += len(events)

        # Store extracted data
        for event in events:
            self._store_event(event)

        return events

    def process_transcript(self, transcript: list[dict[str, Any]]) -> list[Event]:
        """
        Process a full transcript.

        Args:
            transcript: List of conversation turns

        Returns:
            List of all extracted events
        """
        all_events = []
        for turn in transcript:
            events = self.process_turn(turn)
            all_events.extend(events)
        return all_events

    def _store_event(self, event: Event) -> None:
        """Store event data to graph store."""
        if not self._graph_store:
            return

        if event.type == EventType.DECISION:
            self._store_decision(event)
        elif event.type in (EventType.ASSISTANT_MESSAGE, EventType.USER_MESSAGE):
            self._extract_and_store_entities(event)

    def _store_decision(self, event: Event) -> None:
        """Store a decision event to the decisions table."""
        if not self._graph_store or not self.config.extract_decisions:
            return

        if isinstance(event, DecisionEvent):
            if event.confidence >= self.config.min_decision_confidence:
                self._graph_store.add_decision({
                    "action": event.action,
                    "reasoning": event.reasoning,
                    "alternatives": event.alternatives,
                    "confidence": event.confidence,
                })
                self._stats.decisions_stored += 1

    def _extract_and_store_entities(self, event: Event) -> None:
        """Extract and store entities from message content."""
        if not self._graph_store or not self._entity_extractor:
            return

        content = event.data.get("content", "")
        if hasattr(event, "content"):
            content = event.content

        if not content or len(content) < 10:
            return

        try:
            extraction = self._entity_extractor.extract(content)
            entities = extraction.content.get("entities", [])

            for ent in entities:
                self._graph_store.add_entity({
                    "name": ent["name"],
                    "type": ent["type"],
                    "description": ent.get("description") or content[:100],
                })
                self._stats.entities_stored += 1

        except Exception:
            logger.debug("Entity extraction failed for content", exc_info=True)

    def get_stats(self) -> dict[str, Any]:
        """Get watcher statistics."""
        return {
            "turns_processed": self._stats.turns_processed,
            "events_extracted": self._stats.events_extracted,
            "decisions_stored": self._stats.decisions_stored,
            "entities_stored": self._stats.entities_stored,
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = WatcherStats()
