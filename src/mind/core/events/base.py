"""Base event types and envelope for Mind v5."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """All event types in Mind v5.

    Naming: {Domain}{Action} in past tense.
    """

    # Memory events
    MEMORY_CREATED = "memory.created"
    MEMORY_PROMOTED = "memory.promoted"
    MEMORY_RETRIEVAL = "memory.retrieval"
    MEMORY_SALIENCE_ADJUSTED = "memory.salience_adjusted"
    MEMORY_EXPIRED = "memory.expired"

    # Decision events
    DECISION_TRACKED = "decision.tracked"
    OUTCOME_OBSERVED = "outcome.observed"

    # Causal events (Phase 2)
    CAUSAL_EDGE_DISCOVERED = "causal.edge_discovered"
    CAUSAL_EDGE_VALIDATED = "causal.edge_validated"

    # Federation events (Phase 4)
    PATTERN_EXTRACTED = "pattern.extracted"
    PATTERN_FEDERATED = "pattern.federated"


class Event(BaseModel, ABC):
    """Base class for all domain events.

    Events are immutable facts about what happened.
    They are the source of truth for all state.
    """

    @property
    @abstractmethod
    def event_type(self) -> EventType:
        """The type of this event."""
        ...

    @property
    @abstractmethod
    def aggregate_id(self) -> UUID:
        """The ID of the aggregate this event belongs to."""
        ...


class EventEnvelope(BaseModel):
    """Wrapper for events with metadata.

    All events are published wrapped in an envelope.
    The envelope contains routing and tracing information.
    """

    # Identity
    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType

    # Routing
    user_id: UUID
    aggregate_id: UUID

    # Payload
    payload: dict[str, Any]

    # Tracing
    correlation_id: UUID = Field(default_factory=uuid4)
    causation_id: UUID | None = None  # ID of event that caused this one

    # Timing
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1  # Schema version for evolution

    @classmethod
    def wrap(
        cls,
        event: Event,
        user_id: UUID,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> "EventEnvelope":
        """Wrap a domain event in an envelope."""
        return cls(
            event_type=event.event_type,
            user_id=user_id,
            aggregate_id=event.aggregate_id,
            payload=event.model_dump(),
            correlation_id=correlation_id or uuid4(),
            causation_id=causation_id,
        )

    def nats_subject(self) -> str:
        """Generate NATS subject for this event.

        Pattern: mind.{category}.{action}.{user_id}
        """
        # event_type is like "memory.created" -> category="memory", action="created"
        parts = self.event_type.value.split(".")
        category = parts[0]
        action = parts[1] if len(parts) > 1 else "unknown"
        return f"mind.{category}.{action}.{self.user_id}"
