"""Temporal activities for memory management.

Activities are the individual tasks that workflows orchestrate.
They should be idempotent and handle their own retries for
transient failures.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from temporalio import activity

from mind.core.memory.models import Memory, TemporalLevel
from mind.core.events.memory import MemoryPromoted
from mind.infrastructure.postgres.database import get_database
from mind.infrastructure.postgres.repositories import MemoryRepository
from mind.services.events import get_event_service


@dataclass
class PromotionCandidate:
    """A memory that may be eligible for promotion."""

    memory_id: UUID
    user_id: UUID
    current_level: TemporalLevel
    target_level: TemporalLevel
    score: float  # Confidence in promotion decision
    reason: str


@dataclass
class PromotionResult:
    """Result of a memory promotion attempt."""

    memory_id: UUID
    success: bool
    from_level: TemporalLevel | None = None
    to_level: TemporalLevel | None = None
    error: str | None = None


# Promotion criteria thresholds
PROMOTION_THRESHOLDS = {
    # From IMMEDIATE to SITUATIONAL
    (TemporalLevel.IMMEDIATE, TemporalLevel.SITUATIONAL): {
        "min_age_hours": 24,  # At least 1 day old
        "min_retrieval_count": 3,  # Retrieved at least 3 times
        "min_positive_ratio": 0.6,  # 60% positive outcomes
        "min_salience": 0.5,  # Above average salience
    },
    # From SITUATIONAL to SEASONAL
    (TemporalLevel.SITUATIONAL, TemporalLevel.SEASONAL): {
        "min_age_hours": 24 * 7,  # At least 1 week old
        "min_retrieval_count": 10,
        "min_positive_ratio": 0.7,
        "min_salience": 0.6,
    },
    # From SEASONAL to IDENTITY
    (TemporalLevel.SEASONAL, TemporalLevel.IDENTITY): {
        "min_age_hours": 24 * 30,  # At least 1 month old
        "min_retrieval_count": 25,
        "min_positive_ratio": 0.8,
        "min_salience": 0.7,
    },
}


@activity.defn
async def find_promotion_candidates(
    user_id: UUID,
    batch_size: int = 100,
) -> list[PromotionCandidate]:
    """Find memories eligible for promotion.

    This activity scans a user's memories and identifies those that
    meet the criteria for promotion to the next temporal level.

    Criteria include:
    - Age (time since creation)
    - Retrieval frequency
    - Outcome ratio (positive vs negative)
    - Current salience

    Args:
        user_id: User whose memories to evaluate
        batch_size: Maximum candidates to return

    Returns:
        List of promotion candidates ordered by score
    """
    activity.logger.info(f"Finding promotion candidates for user {user_id}")

    candidates = []
    db = get_database()

    async with db.session() as session:
        repo = MemoryRepository(session)

        # Check each level for promotion opportunities
        for from_level in [TemporalLevel.IMMEDIATE, TemporalLevel.SITUATIONAL, TemporalLevel.SEASONAL]:
            to_level = TemporalLevel(from_level.value + 1)
            thresholds = PROMOTION_THRESHOLDS.get((from_level, to_level))

            if not thresholds:
                continue

            # Query memories at this level
            result = await repo.retrieve(
                user_id=user_id,
                temporal_levels=[from_level],
                limit=batch_size,
            )

            if not result.is_ok:
                activity.logger.warning(f"Failed to query level {from_level}: {result.error}")
                continue

            for scored_memory in result.value.memories:
                memory = scored_memory.memory

                # Check age
                age_hours = (datetime.now(UTC) - memory.created_at).total_seconds() / 3600
                if age_hours < thresholds["min_age_hours"]:
                    continue

                # Check retrieval count
                if memory.retrieval_count < thresholds["min_retrieval_count"]:
                    continue

                # Check outcome ratio
                total_outcomes = memory.positive_outcomes + memory.negative_outcomes
                if total_outcomes > 0:
                    positive_ratio = memory.positive_outcomes / total_outcomes
                    if positive_ratio < thresholds["min_positive_ratio"]:
                        continue

                # Check salience
                if memory.effective_salience < thresholds["min_salience"]:
                    continue

                # Calculate promotion score (higher is better)
                score = _calculate_promotion_score(memory, thresholds)

                candidates.append(PromotionCandidate(
                    memory_id=memory.memory_id,
                    user_id=memory.user_id,
                    current_level=from_level,
                    target_level=to_level,
                    score=score,
                    reason=f"Met all criteria: age={age_hours:.0f}h, retrievals={memory.retrieval_count}, "
                           f"salience={memory.effective_salience:.2f}",
                ))

    # Sort by score and limit
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:batch_size]


def _calculate_promotion_score(memory: Memory, thresholds: dict) -> float:
    """Calculate a promotion confidence score for a memory.

    Higher scores indicate stronger candidates for promotion.
    """
    # Factors that increase score
    age_factor = min(1.0, (datetime.now(UTC) - memory.created_at).total_seconds() / 3600 / thresholds["min_age_hours"])
    retrieval_factor = min(1.0, memory.retrieval_count / (thresholds["min_retrieval_count"] * 2))
    salience_factor = memory.effective_salience

    # Outcome factor (heavily weighted)
    total_outcomes = memory.positive_outcomes + memory.negative_outcomes
    if total_outcomes > 0:
        outcome_factor = memory.positive_outcomes / total_outcomes
    else:
        outcome_factor = 0.5  # Neutral if no outcomes

    # Weighted average
    score = (
        age_factor * 0.15 +
        retrieval_factor * 0.25 +
        salience_factor * 0.25 +
        outcome_factor * 0.35
    )

    return min(1.0, max(0.0, score))


@activity.defn
async def promote_memory(
    candidate: PromotionCandidate,
) -> PromotionResult:
    """Promote a single memory to the next temporal level.

    This is an idempotent operation - if the memory has already
    been promoted, it returns success without modifying.

    Args:
        candidate: The promotion candidate

    Returns:
        Result of the promotion attempt
    """
    activity.logger.info(
        f"Promoting memory {candidate.memory_id} from "
        f"{candidate.current_level.name} to {candidate.target_level.name}"
    )

    db = get_database()

    async with db.session() as session:
        repo = MemoryRepository(session)

        # Get current memory state
        result = await repo.get(candidate.memory_id)
        if not result.is_ok:
            return PromotionResult(
                memory_id=candidate.memory_id,
                success=False,
                error=f"Memory not found: {result.error.message}",
            )

        memory = result.value

        # Check if already promoted (idempotency)
        if memory.temporal_level.value >= candidate.target_level.value:
            activity.logger.info(f"Memory {candidate.memory_id} already at level {memory.temporal_level.name}")
            return PromotionResult(
                memory_id=candidate.memory_id,
                success=True,
                from_level=candidate.current_level,
                to_level=memory.temporal_level,
            )

        # Perform promotion by updating the memory
        # Note: In a full implementation, we'd create a new memory version
        # Here we update in place for simplicity
        promoted_memory = Memory(
            memory_id=memory.memory_id,
            user_id=memory.user_id,
            content=memory.content,
            content_type=memory.content_type,
            temporal_level=candidate.target_level,
            valid_from=memory.valid_from,
            valid_until=memory.valid_until,
            base_salience=memory.base_salience,
            outcome_adjustment=memory.outcome_adjustment,
            retrieval_count=memory.retrieval_count,
            decision_count=memory.decision_count,
            positive_outcomes=memory.positive_outcomes,
            negative_outcomes=memory.negative_outcomes,
            promoted_from_level=memory.temporal_level,
            promotion_timestamp=datetime.now(UTC),
            created_at=memory.created_at,
        )

        # Update in database (would use a dedicated update method in production)
        # For now, we'll use a direct SQL update
        from sqlalchemy import update, text
        from mind.infrastructure.postgres.models import MemoryModel

        await session.execute(
            update(MemoryModel)
            .where(MemoryModel.memory_id == candidate.memory_id)
            .values(
                temporal_level=candidate.target_level.value,
                promoted_from_level=candidate.current_level.value,
                promotion_timestamp=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        await session.commit()

    return PromotionResult(
        memory_id=candidate.memory_id,
        success=True,
        from_level=candidate.current_level,
        to_level=candidate.target_level,
    )


@activity.defn
async def notify_promotion(
    result: PromotionResult,
    user_id: UUID,
) -> bool:
    """Publish event for a successful memory promotion.

    This activity handles the event publishing for promoted memories.
    It's separated from the promotion itself to allow for retry
    without re-promoting.

    Args:
        result: The promotion result
        user_id: User ID for the event

    Returns:
        True if notification succeeded
    """
    if not result.success or not result.from_level or not result.to_level:
        return False

    activity.logger.info(f"Publishing promotion event for {result.memory_id}")

    try:
        event_service = get_event_service()

        event = MemoryPromoted(
            memory_id=result.memory_id,
            from_level=result.from_level,
            to_level=result.to_level,
            reason="Met promotion criteria",
        )

        from mind.infrastructure.nats.client import get_nats_client
        from mind.infrastructure.nats.publisher import EventPublisher

        client = await get_nats_client()
        publisher = EventPublisher(client)

        await publisher.publish_event(
            event=event,
            user_id=user_id,
        )

        return True

    except Exception as e:
        activity.logger.warning(f"Failed to publish promotion event: {e}")
        return False
