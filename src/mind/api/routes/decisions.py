"""Decision tracking API endpoints."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mind.api.schemas.decision import (
    TrackRequest,
    TrackResponse,
    OutcomeRequest,
    OutcomeResponse,
)
from mind.core.decision.models import DecisionTrace, Outcome, SalienceUpdate
from mind.infrastructure.postgres.database import get_database
from mind.infrastructure.postgres.repositories import DecisionRepository, MemoryRepository

router = APIRouter()


@router.post("/track", response_model=TrackResponse, status_code=201)
async def track_decision(request: TrackRequest) -> TrackResponse:
    """Track a decision and the memories that influenced it.

    This creates a decision trace that links the retrieved memories
    to the decision made. Later, when the outcome is observed,
    we can attribute success/failure to specific memories and
    adjust their salience.
    """
    trace = DecisionTrace(
        trace_id=uuid4(),
        user_id=request.user_id,
        session_id=request.session_id,
        memory_ids=request.memory_ids,
        memory_scores=request.memory_scores or {},
        decision_type=request.decision_type,
        decision_summary=request.decision_summary,
        confidence=request.confidence,
        alternatives_count=request.alternatives_count,
    )

    db = get_database()
    async with db.session() as session:
        repo = DecisionRepository(session)
        result = await repo.create_trace(trace)

        if not result.is_ok:
            raise HTTPException(status_code=400, detail=result.error.to_dict())

        return TrackResponse(
            trace_id=result.value.trace_id,
            created_at=result.value.created_at,
        )


@router.post("/outcome", response_model=OutcomeResponse)
async def observe_outcome(request: OutcomeRequest) -> OutcomeResponse:
    """Record an outcome for a previous decision.

    This is the feedback loop that enables learning. When we observe
    that a decision led to a good or bad outcome, we update the
    salience of the memories that influenced that decision.

    Positive outcomes increase memory salience, making those memories
    more likely to be retrieved in similar future situations.
    Negative outcomes decrease salience.
    """
    outcome = Outcome(
        trace_id=request.trace_id,
        quality=request.quality,
        signal=request.signal,
        feedback_text=request.feedback,
    )

    db = get_database()
    async with db.session() as session:
        decision_repo = DecisionRepository(session)
        memory_repo = MemoryRepository(session)

        # Get the trace
        trace_result = await decision_repo.get_trace(request.trace_id)
        if not trace_result.is_ok:
            raise HTTPException(status_code=404, detail=trace_result.error.to_dict())

        trace = trace_result.value

        # Calculate attribution (simple: proportional to retrieval score)
        total_score = sum(trace.memory_scores.values()) or 1.0
        attributions = {
            mid: score / total_score
            for mid, score in trace.memory_scores.items()
        }

        # Record outcome
        result = await decision_repo.record_outcome(
            trace_id=request.trace_id,
            outcome=outcome,
            attributions=attributions,
        )

        if not result.is_ok:
            raise HTTPException(status_code=400, detail=result.error.to_dict())

        # Update memory salience
        salience_updates = []
        for memory_id, contribution in attributions.items():
            update = SalienceUpdate.from_outcome(
                memory_id=UUID(memory_id),
                trace_id=request.trace_id,
                outcome=outcome,
                contribution=contribution,
            )
            salience_updates.append(update)

            await memory_repo.update_salience(
                memory_id=UUID(memory_id),
                adjustment=update,
            )

        return OutcomeResponse(
            trace_id=request.trace_id,
            outcome_quality=outcome.quality,
            memories_updated=len(salience_updates),
            salience_changes={
                str(u.memory_id): u.delta for u in salience_updates
            },
        )
