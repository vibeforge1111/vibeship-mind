"""Memory API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from mind.core.memory.models import Memory, TemporalLevel


class MemoryCreate(BaseModel):
    """Request to create a memory."""

    user_id: UUID
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: str = Field(
        default="observation",
        description="Type: fact, preference, event, goal, observation",
    )
    temporal_level: TemporalLevel = Field(
        default=TemporalLevel.IMMEDIATE,
        description="Temporal level: 1=immediate, 2=situational, 3=seasonal, 4=identity",
    )
    salience: float = Field(default=1.0, ge=0.0, le=1.0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class MemoryResponse(BaseModel):
    """Memory in API responses."""

    memory_id: UUID
    user_id: UUID
    content: str
    content_type: str
    temporal_level: int
    temporal_level_name: str
    effective_salience: float
    retrieval_count: int
    decision_count: int
    positive_outcomes: int
    negative_outcomes: int
    valid_from: datetime
    valid_until: datetime | None
    created_at: datetime

    @classmethod
    def from_domain(cls, memory: Memory) -> "MemoryResponse":
        """Create from domain model."""
        return cls(
            memory_id=memory.memory_id,
            user_id=memory.user_id,
            content=memory.content,
            content_type=memory.content_type,
            temporal_level=memory.temporal_level.value,
            temporal_level_name=memory.temporal_level.name.lower(),
            effective_salience=memory.effective_salience,
            retrieval_count=memory.retrieval_count,
            decision_count=memory.decision_count,
            positive_outcomes=memory.positive_outcomes,
            negative_outcomes=memory.negative_outcomes,
            valid_from=memory.valid_from,
            valid_until=memory.valid_until,
            created_at=memory.created_at,
        )


class RetrieveRequest(BaseModel):
    """Request to retrieve memories."""

    user_id: UUID
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    temporal_levels: list[TemporalLevel] | None = Field(
        default=None,
        description="Filter by temporal levels (default: all)",
    )
    min_salience: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum effective salience",
    )


class RetrieveResponse(BaseModel):
    """Response from memory retrieval."""

    retrieval_id: UUID
    memories: list[MemoryResponse]
    scores: dict[str, float] = Field(
        description="Memory ID to retrieval score mapping"
    )
    latency_ms: float
