"""Core memory models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from uuid import UUID


class TemporalLevel(IntEnum):
    """Hierarchical temporal memory levels.

    Memories exist at one level and can be promoted upward
    as they prove stable and valuable over time.
    """

    IMMEDIATE = 1  # Session-level, working memory (hours)
    SITUATIONAL = 2  # Task/project context (days-weeks)
    SEASONAL = 3  # Recurring patterns, projects (weeks-months)
    IDENTITY = 4  # Core values, stable preferences (months-years)

    @property
    def description(self) -> str:
        """Human-readable description of this level."""
        descriptions = {
            TemporalLevel.IMMEDIATE: "Current session, working memory",
            TemporalLevel.SITUATIONAL: "Active tasks, recent events",
            TemporalLevel.SEASONAL: "Projects, recurring patterns",
            TemporalLevel.IDENTITY: "Core values, stable preferences",
        }
        return descriptions[self]

    @property
    def typical_duration_days(self) -> int:
        """Typical duration for memories at this level."""
        durations = {
            TemporalLevel.IMMEDIATE: 1,
            TemporalLevel.SITUATIONAL: 14,
            TemporalLevel.SEASONAL: 90,
            TemporalLevel.IDENTITY: 365,
        }
        return durations[self]


@dataclass(frozen=True)
class Memory:
    """A single memory unit in the hierarchical memory system.

    Memories are immutable once created. Updates create new versions.
    Salience is adjusted based on decision outcomes.
    """

    memory_id: UUID
    user_id: UUID
    content: str
    content_type: str  # "fact", "preference", "event", "goal", "observation"
    temporal_level: TemporalLevel
    valid_from: datetime
    valid_until: datetime | None  # None = still valid

    # Salience tracking
    base_salience: float  # Initial importance (0.0 - 1.0)
    outcome_adjustment: float = 0.0  # Learned adjustment from outcomes

    # Usage statistics
    retrieval_count: int = 0
    decision_count: int = 0
    positive_outcomes: int = 0
    negative_outcomes: int = 0

    # Promotion tracking
    promoted_from_level: TemporalLevel | None = None
    promotion_timestamp: datetime | None = None

    # Timestamps
    created_at: datetime = None  # type: ignore
    updated_at: datetime = None  # type: ignore

    def __post_init__(self) -> None:
        """Set default timestamps if not provided."""
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(UTC))
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", datetime.now(UTC))

    @property
    def effective_salience(self) -> float:
        """Salience after outcome-based adjustment.

        Clamped to [0.0, 1.0] range.
        """
        return max(0.0, min(1.0, self.base_salience + self.outcome_adjustment))

    @property
    def is_valid(self) -> bool:
        """Check if memory is currently valid."""
        now = datetime.now(UTC)
        if self.valid_until is not None and now > self.valid_until:
            return False
        return now >= self.valid_from

    @property
    def outcome_ratio(self) -> float | None:
        """Ratio of positive to total outcomes.

        Returns None if no outcomes recorded.
        """
        total = self.positive_outcomes + self.negative_outcomes
        if total == 0:
            return None
        return self.positive_outcomes / total

    def with_outcome_adjustment(self, delta: float) -> "Memory":
        """Return new Memory with adjusted salience. Original unchanged."""
        return Memory(
            memory_id=self.memory_id,
            user_id=self.user_id,
            content=self.content,
            content_type=self.content_type,
            temporal_level=self.temporal_level,
            valid_from=self.valid_from,
            valid_until=self.valid_until,
            base_salience=self.base_salience,
            outcome_adjustment=self.outcome_adjustment + delta,
            retrieval_count=self.retrieval_count,
            decision_count=self.decision_count,
            positive_outcomes=self.positive_outcomes,
            negative_outcomes=self.negative_outcomes,
            promoted_from_level=self.promoted_from_level,
            promotion_timestamp=self.promotion_timestamp,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )

    def with_retrieval(self) -> "Memory":
        """Return new Memory with incremented retrieval count."""
        return Memory(
            memory_id=self.memory_id,
            user_id=self.user_id,
            content=self.content,
            content_type=self.content_type,
            temporal_level=self.temporal_level,
            valid_from=self.valid_from,
            valid_until=self.valid_until,
            base_salience=self.base_salience,
            outcome_adjustment=self.outcome_adjustment,
            retrieval_count=self.retrieval_count + 1,
            decision_count=self.decision_count,
            positive_outcomes=self.positive_outcomes,
            negative_outcomes=self.negative_outcomes,
            promoted_from_level=self.promoted_from_level,
            promotion_timestamp=self.promotion_timestamp,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )
