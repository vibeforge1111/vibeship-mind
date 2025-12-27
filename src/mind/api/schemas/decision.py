"""Decision tracking API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TrackRequest(BaseModel):
    """Request to track a decision."""

    user_id: UUID
    session_id: UUID
    memory_ids: list[UUID] = Field(
        description="IDs of memories that influenced this decision"
    )
    memory_scores: dict[str, float] | None = Field(
        default=None,
        description="Memory ID to retrieval score mapping",
    )
    decision_type: str = Field(
        description="Type of decision: recommendation, action, preference, etc."
    )
    decision_summary: str = Field(
        max_length=500,
        description="Short summary of the decision (no PII)",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives_count: int = Field(default=0, ge=0)


class TrackResponse(BaseModel):
    """Response from tracking a decision."""

    trace_id: UUID
    created_at: datetime


class OutcomeRequest(BaseModel):
    """Request to record an outcome."""

    trace_id: UUID = Field(description="Decision trace to update")
    quality: float = Field(
        ge=-1.0,
        le=1.0,
        description="Outcome quality: -1 (bad) to 1 (good)",
    )
    signal: str = Field(
        description="How detected: explicit_feedback, implicit_success, etc."
    )
    feedback: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional textual feedback",
    )


class OutcomeResponse(BaseModel):
    """Response from recording an outcome."""

    trace_id: UUID
    outcome_quality: float
    memories_updated: int
    salience_changes: dict[str, float] = Field(
        description="Memory ID to salience delta mapping"
    )
