"""Decision-related events."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from mind.core.events.base import Event, EventType


class DecisionTracked(Event):
    """A decision was tracked with its context."""

    trace_id: UUID
    session_id: UUID

    # Context used
    memory_ids: list[UUID]
    memory_scores: dict[str, float] = Field(default_factory=dict)  # memory_id -> score

    # Decision made
    decision_type: str
    decision_summary: str  # Short summary, no PII
    confidence: float
    alternatives_count: int = 0

    @property
    def event_type(self) -> EventType:
        return EventType.DECISION_TRACKED

    @property
    def aggregate_id(self) -> UUID:
        return self.trace_id


class OutcomeObserved(Event):
    """An outcome was observed for a previous decision."""

    trace_id: UUID
    outcome_quality: float  # -1.0 to 1.0
    outcome_signal: str  # How we detected: "explicit_feedback", "implicit_success", etc.
    observed_at: datetime

    # Attribution (computed)
    memory_attributions: dict[str, float] = Field(
        default_factory=dict
    )  # memory_id -> contribution

    @property
    def event_type(self) -> EventType:
        return EventType.OUTCOME_OBSERVED

    @property
    def aggregate_id(self) -> UUID:
        return self.trace_id
