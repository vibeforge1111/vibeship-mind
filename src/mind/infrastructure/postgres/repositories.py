"""Repository pattern for database operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from mind.core.errors import ErrorCode, MindError, Result
from mind.core.memory.models import Memory, TemporalLevel
from mind.core.memory.retrieval import RetrievalRequest, RetrievalResult, ScoredMemory
from mind.core.decision.models import DecisionTrace, Outcome, SalienceUpdate
from mind.infrastructure.postgres.models import (
    MemoryModel,
    DecisionTraceModel,
    EventModel,
    SalienceAdjustmentModel,
)


class MemoryRepository:
    """Repository for memory operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, memory: Memory, embedding: list[float] | None = None) -> Result[Memory]:
        """Create a new memory."""
        model = MemoryModel(
            memory_id=memory.memory_id,
            user_id=memory.user_id,
            content=memory.content,
            content_type=memory.content_type,
            embedding=embedding,
            temporal_level=memory.temporal_level.value,
            valid_from=memory.valid_from,
            valid_until=memory.valid_until,
            base_salience=memory.base_salience,
            outcome_adjustment=memory.outcome_adjustment,
            retrieval_count=memory.retrieval_count,
            decision_count=memory.decision_count,
            positive_outcomes=memory.positive_outcomes,
            negative_outcomes=memory.negative_outcomes,
            promoted_from_level=memory.promoted_from_level.value if memory.promoted_from_level else None,
            promotion_timestamp=memory.promotion_timestamp,
        )
        self._session.add(model)
        await self._session.flush()
        return Result.ok(memory)

    async def get(self, memory_id: UUID) -> Result[Memory]:
        """Get a memory by ID."""
        stmt = select(MemoryModel).where(MemoryModel.memory_id == memory_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return Result.err(
                MindError(
                    code=ErrorCode.MEMORY_NOT_FOUND,
                    message=f"Memory {memory_id} not found",
                    context={"memory_id": str(memory_id)},
                )
            )

        return Result.ok(self._to_domain(model))

    async def retrieve(self, request: RetrievalRequest) -> Result[RetrievalResult]:
        """Retrieve memories using multi-source fusion."""
        start_time = datetime.now(UTC)

        # Build base query
        stmt = select(MemoryModel).where(MemoryModel.user_id == request.user_id)

        # Filter by temporal levels
        if request.temporal_levels:
            levels = [level.value for level in request.temporal_levels]
            stmt = stmt.where(MemoryModel.temporal_level.in_(levels))

        # Filter by salience
        if request.min_salience > 0:
            stmt = stmt.where(
                (MemoryModel.base_salience + MemoryModel.outcome_adjustment) >= request.min_salience
            )

        # Filter expired
        if not request.include_expired:
            now = datetime.now(UTC)
            stmt = stmt.where(
                (MemoryModel.valid_until.is_(None)) | (MemoryModel.valid_until > now)
            )
            stmt = stmt.where(MemoryModel.valid_from <= now)

        # Order by effective salience and limit
        stmt = stmt.order_by(
            (MemoryModel.base_salience + MemoryModel.outcome_adjustment).desc()
        ).limit(request.limit * 3)  # Over-fetch for reranking

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        # Convert to scored memories
        scored_memories = []
        for i, model in enumerate(models[: request.limit]):
            memory = self._to_domain(model)
            scored = ScoredMemory(
                memory=memory,
                salience_score=memory.effective_salience,
                final_score=memory.effective_salience,  # Simple for now
                rank=i + 1,
            )
            scored_memories.append(scored)

        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        return Result.ok(
            RetrievalResult(
                memories=scored_memories,
                query=request.query,
                latency_ms=latency_ms,
            )
        )

    async def vector_search(
        self,
        user_id: UUID,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[tuple[MemoryModel, float]]:
        """Search memories by vector similarity."""
        # Use pgvector cosine distance
        stmt = (
            select(
                MemoryModel,
                (1 - MemoryModel.embedding.cosine_distance(query_embedding)).label("similarity"),
            )
            .where(MemoryModel.user_id == user_id)
            .where(MemoryModel.embedding.isnot(None))
            .order_by(MemoryModel.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def update_salience(
        self,
        memory_id: UUID,
        adjustment: SalienceUpdate,
    ) -> Result[Memory]:
        """Update memory salience based on outcome."""
        stmt = select(MemoryModel).where(MemoryModel.memory_id == memory_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return Result.err(
                MindError(
                    code=ErrorCode.MEMORY_NOT_FOUND,
                    message=f"Memory {memory_id} not found",
                )
            )

        # Log the adjustment
        log = SalienceAdjustmentModel(
            memory_id=memory_id,
            trace_id=adjustment.trace_id,
            previous_adjustment=model.outcome_adjustment,
            new_adjustment=model.outcome_adjustment + adjustment.delta,
            delta=adjustment.delta,
            reason=adjustment.reason,
        )
        self._session.add(log)

        # Update the memory
        model.outcome_adjustment += adjustment.delta
        if adjustment.delta > 0:
            model.positive_outcomes += 1
        else:
            model.negative_outcomes += 1

        await self._session.flush()
        return Result.ok(self._to_domain(model))

    def _to_domain(self, model: MemoryModel) -> Memory:
        """Convert SQLAlchemy model to domain object."""
        return Memory(
            memory_id=model.memory_id,
            user_id=model.user_id,
            content=model.content,
            content_type=model.content_type,
            temporal_level=TemporalLevel(model.temporal_level),
            valid_from=model.valid_from,
            valid_until=model.valid_until,
            base_salience=model.base_salience,
            outcome_adjustment=model.outcome_adjustment,
            retrieval_count=model.retrieval_count,
            decision_count=model.decision_count,
            positive_outcomes=model.positive_outcomes,
            negative_outcomes=model.negative_outcomes,
            promoted_from_level=TemporalLevel(model.promoted_from_level) if model.promoted_from_level else None,
            promotion_timestamp=model.promotion_timestamp,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class DecisionRepository:
    """Repository for decision tracking."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_trace(self, trace: DecisionTrace) -> Result[DecisionTrace]:
        """Create a new decision trace."""
        model = DecisionTraceModel(
            trace_id=trace.trace_id,
            user_id=trace.user_id,
            session_id=trace.session_id,
            context_memory_ids=[str(mid) for mid in trace.memory_ids],
            memory_scores=trace.memory_scores,
            decision_type=trace.decision_type,
            decision_summary=trace.decision_summary,
            confidence=trace.confidence,
            alternatives_count=trace.alternatives_count,
        )
        self._session.add(model)
        await self._session.flush()
        return Result.ok(trace)

    async def get_trace(self, trace_id: UUID) -> Result[DecisionTrace]:
        """Get a decision trace by ID."""
        stmt = select(DecisionTraceModel).where(DecisionTraceModel.trace_id == trace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return Result.err(
                MindError(
                    code=ErrorCode.DECISION_NOT_FOUND,
                    message=f"Decision trace {trace_id} not found",
                )
            )

        return Result.ok(self._to_domain(model))

    async def record_outcome(
        self,
        trace_id: UUID,
        outcome: Outcome,
        attributions: dict[str, float],
    ) -> Result[DecisionTrace]:
        """Record an outcome for a decision trace."""
        stmt = select(DecisionTraceModel).where(DecisionTraceModel.trace_id == trace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return Result.err(
                MindError(
                    code=ErrorCode.DECISION_NOT_FOUND,
                    message=f"Decision trace {trace_id} not found",
                )
            )

        if model.outcome_observed:
            return Result.err(
                MindError(
                    code=ErrorCode.DECISION_ALREADY_OBSERVED,
                    message=f"Outcome already recorded for trace {trace_id}",
                )
            )

        model.outcome_observed = True
        model.outcome_quality = outcome.quality
        model.outcome_timestamp = outcome.observed_at
        model.outcome_signal = outcome.signal
        model.memory_attribution = attributions

        await self._session.flush()
        return Result.ok(self._to_domain(model))

    async def get_pending_traces(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> list[DecisionTrace]:
        """Get traces without observed outcomes."""
        stmt = (
            select(DecisionTraceModel)
            .where(DecisionTraceModel.user_id == user_id)
            .where(DecisionTraceModel.outcome_observed == False)
            .order_by(DecisionTraceModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    def _to_domain(self, model: DecisionTraceModel) -> DecisionTrace:
        """Convert SQLAlchemy model to domain object."""
        return DecisionTrace(
            trace_id=model.trace_id,
            user_id=model.user_id,
            session_id=model.session_id,
            memory_ids=[UUID(mid) for mid in model.context_memory_ids],
            memory_scores=model.memory_scores,
            decision_type=model.decision_type,
            decision_summary=model.decision_summary,
            confidence=model.confidence,
            alternatives_count=model.alternatives_count,
            created_at=model.created_at,
            outcome_observed=model.outcome_observed,
            outcome_quality=model.outcome_quality,
            outcome_timestamp=model.outcome_timestamp,
            outcome_signal=model.outcome_signal,
        )


class EventRepository:
    """Repository for event sourcing."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def append(self, event: EventModel) -> Result[EventModel]:
        """Append an event to the log."""
        self._session.add(event)
        await self._session.flush()
        return Result.ok(event)

    async def get_by_aggregate(
        self,
        aggregate_id: UUID,
        after_version: int = 0,
    ) -> list[EventModel]:
        """Get events for an aggregate."""
        stmt = (
            select(EventModel)
            .where(EventModel.aggregate_id == aggregate_id)
            .where(EventModel.version > after_version)
            .order_by(EventModel.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: UUID,
        event_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[EventModel]:
        """Get events for a user."""
        stmt = select(EventModel).where(EventModel.user_id == user_id)

        if event_types:
            stmt = stmt.where(EventModel.event_type.in_(event_types))

        stmt = stmt.order_by(EventModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
