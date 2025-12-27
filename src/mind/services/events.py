"""Event service for publishing domain events."""

from uuid import UUID

import structlog

from mind.core.errors import Result
from mind.core.events.base import Event, EventEnvelope
from mind.core.events.memory import (
    MemoryCreated,
    MemoryRetrieval,
    MemorySalienceAdjusted,
    RetrievedMemory,
)
from mind.core.events.decision import DecisionTracked, OutcomeObserved
from mind.core.memory.models import Memory
from mind.core.decision.models import DecisionTrace, Outcome
from mind.infrastructure.nats.client import get_nats_client, NatsClient
from mind.infrastructure.nats.publisher import EventPublisher

logger = structlog.get_logger()


class EventService:
    """Service for publishing domain events to NATS.

    This service provides high-level methods for publishing domain
    events. It handles connection management and wraps events in
    envelopes with proper correlation IDs.
    """

    def __init__(self, client: NatsClient | None = None):
        self._client = client
        self._publisher: EventPublisher | None = None

    async def _ensure_publisher(self) -> EventPublisher:
        """Lazily initialize publisher."""
        if self._publisher is None:
            if self._client is None:
                self._client = await get_nats_client()
            self._publisher = EventPublisher(self._client)
        return self._publisher

    async def publish_memory_created(
        self,
        memory: Memory,
        correlation_id: UUID | None = None,
    ) -> Result[None]:
        """Publish a MemoryCreated event."""
        try:
            publisher = await self._ensure_publisher()

            event = MemoryCreated(
                memory_id=memory.memory_id,
                content=memory.content,
                content_type=memory.content_type,
                temporal_level=memory.temporal_level,
                base_salience=memory.base_salience,
                valid_from=memory.valid_from,
            )

            result = await publisher.publish_event(
                event=event,
                user_id=memory.user_id,
                correlation_id=correlation_id,
            )

            if result.is_ok:
                return Result.ok(None)
            return Result.err(result.error)

        except Exception as e:
            logger.warning("event_publish_skipped", error=str(e), event_type="memory.created")
            # Don't fail the operation if event publishing fails
            return Result.ok(None)

    async def publish_memory_retrieval(
        self,
        user_id: UUID,
        retrieval_id: UUID,
        query: str,
        memories: list[tuple[UUID, int, float, str]],  # (memory_id, rank, score, source)
        latency_ms: float,
        trace_id: UUID | None = None,
        correlation_id: UUID | None = None,
    ) -> Result[None]:
        """Publish a MemoryRetrieval event."""
        try:
            publisher = await self._ensure_publisher()

            retrieved = [
                RetrievedMemory(
                    memory_id=mid,
                    rank=rank,
                    score=score,
                    source=source,
                )
                for mid, rank, score, source in memories
            ]

            event = MemoryRetrieval(
                retrieval_id=retrieval_id,
                query=query,
                memories=retrieved,
                latency_ms=latency_ms,
                trace_id=trace_id,
            )

            result = await publisher.publish_event(
                event=event,
                user_id=user_id,
                correlation_id=correlation_id,
            )

            if result.is_ok:
                return Result.ok(None)
            return Result.err(result.error)

        except Exception as e:
            logger.warning("event_publish_skipped", error=str(e), event_type="memory.retrieval")
            return Result.ok(None)

    async def publish_salience_adjusted(
        self,
        user_id: UUID,
        memory_id: UUID,
        trace_id: UUID,
        previous_adjustment: float,
        new_adjustment: float,
        delta: float,
        reason: str,
        correlation_id: UUID | None = None,
    ) -> Result[None]:
        """Publish a MemorySalienceAdjusted event."""
        try:
            publisher = await self._ensure_publisher()

            event = MemorySalienceAdjusted(
                memory_id=memory_id,
                trace_id=trace_id,
                previous_adjustment=previous_adjustment,
                new_adjustment=new_adjustment,
                delta=delta,
                reason=reason,
            )

            result = await publisher.publish_event(
                event=event,
                user_id=user_id,
                correlation_id=correlation_id,
            )

            if result.is_ok:
                return Result.ok(None)
            return Result.err(result.error)

        except Exception as e:
            logger.warning("event_publish_skipped", error=str(e), event_type="memory.salience_adjusted")
            return Result.ok(None)

    async def publish_decision_tracked(
        self,
        trace: DecisionTrace,
        correlation_id: UUID | None = None,
    ) -> Result[None]:
        """Publish a DecisionTracked event."""
        try:
            publisher = await self._ensure_publisher()

            event = DecisionTracked(
                trace_id=trace.trace_id,
                session_id=trace.session_id,
                memory_ids=trace.memory_ids,
                memory_scores=trace.memory_scores,
                decision_type=trace.decision_type,
                decision_summary=trace.decision_summary,
                confidence=trace.confidence,
                alternatives_count=trace.alternatives_count,
            )

            result = await publisher.publish_event(
                event=event,
                user_id=trace.user_id,
                correlation_id=correlation_id,
            )

            if result.is_ok:
                return Result.ok(None)
            return Result.err(result.error)

        except Exception as e:
            logger.warning("event_publish_skipped", error=str(e), event_type="decision.tracked")
            return Result.ok(None)

    async def publish_outcome_observed(
        self,
        user_id: UUID,
        trace_id: UUID,
        outcome: Outcome,
        attributions: dict[str, float],
        correlation_id: UUID | None = None,
    ) -> Result[None]:
        """Publish an OutcomeObserved event."""
        try:
            publisher = await self._ensure_publisher()

            event = OutcomeObserved(
                trace_id=trace_id,
                outcome_quality=outcome.quality,
                outcome_signal=outcome.signal,
                observed_at=outcome.observed_at,
                memory_attributions=attributions,
            )

            result = await publisher.publish_event(
                event=event,
                user_id=user_id,
                correlation_id=correlation_id,
            )

            if result.is_ok:
                return Result.ok(None)
            return Result.err(result.error)

        except Exception as e:
            logger.warning("event_publish_skipped", error=str(e), event_type="outcome.observed")
            return Result.ok(None)


# Global event service instance
_event_service: EventService | None = None


def get_event_service() -> EventService:
    """Get or create event service instance."""
    global _event_service
    if _event_service is None:
        _event_service = EventService()
    return _event_service
