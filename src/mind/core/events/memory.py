"""Memory-related events."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from mind.core.events.base import Event, EventType
from mind.core.memory.models import TemporalLevel


class MemoryCreated(Event):
    """A new memory was created."""

    memory_id: UUID
    content: str
    content_type: str
    temporal_level: TemporalLevel
    base_salience: float = 1.0
    valid_from: datetime
    source_event_id: UUID | None = None  # What triggered this memory

    @property
    def event_type(self) -> EventType:
        return EventType.MEMORY_CREATED

    @property
    def aggregate_id(self) -> UUID:
        return self.memory_id


class MemoryPromoted(Event):
    """A memory was promoted to a higher temporal level."""

    memory_id: UUID
    from_level: TemporalLevel
    to_level: TemporalLevel
    reason: str  # Why it was promoted

    @property
    def event_type(self) -> EventType:
        return EventType.MEMORY_PROMOTED

    @property
    def aggregate_id(self) -> UUID:
        return self.memory_id


class RetrievedMemory(BaseModel):
    """A memory that was retrieved."""

    memory_id: UUID
    rank: int
    score: float
    source: str  # "vector", "keyword", "graph"


class MemoryRetrieval(Event):
    """Memories were retrieved for a query."""

    retrieval_id: UUID
    query: str
    memories: list[RetrievedMemory]
    latency_ms: float
    trace_id: UUID | None = None  # Link to decision trace if applicable

    @property
    def event_type(self) -> EventType:
        return EventType.MEMORY_RETRIEVAL

    @property
    def aggregate_id(self) -> UUID:
        return self.retrieval_id


class MemorySalienceAdjusted(Event):
    """A memory's salience was adjusted based on outcome."""

    memory_id: UUID
    trace_id: UUID  # Decision trace that triggered adjustment
    previous_adjustment: float
    new_adjustment: float
    delta: float
    reason: str  # "positive_outcome", "negative_outcome", "decay"

    @property
    def event_type(self) -> EventType:
        return EventType.MEMORY_SALIENCE_ADJUSTED

    @property
    def aggregate_id(self) -> UUID:
        return self.memory_id
