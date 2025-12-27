"""Decision tracking models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(frozen=True)
class DecisionTrace:
    """Tracks a decision and the context used to make it.

    This is the core mechanism for outcome-weighted learning.
    We track which memories influenced a decision, then observe
    the outcome to adjust memory salience.
    """

    trace_id: UUID
    user_id: UUID
    session_id: UUID

    # Context used (snapshot at decision time)
    memory_ids: list[UUID]
    memory_scores: dict[str, float]  # memory_id -> retrieval score

    # Decision made
    decision_type: str  # "recommendation", "action", "preference", etc.
    decision_summary: str  # Short summary (no PII)
    confidence: float  # 0.0 - 1.0
    alternatives_count: int = 0

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Outcome (filled later)
    outcome_observed: bool = False
    outcome_quality: float | None = None  # -1.0 to 1.0
    outcome_timestamp: datetime | None = None
    outcome_signal: str | None = None


@dataclass(frozen=True)
class Outcome:
    """An observed outcome for a decision.

    Outcomes can be:
    - Explicit: User feedback ("this was helpful")
    - Implicit: Behavioral signals (user accepted recommendation)
    - Inferred: System observation (task completed successfully)
    """

    trace_id: UUID
    quality: float  # -1.0 (bad) to 1.0 (good)
    signal: str  # How we detected: "explicit_positive", "implicit_acceptance", etc.
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Optional feedback
    feedback_text: str | None = None

    def is_positive(self) -> bool:
        """Check if outcome is positive."""
        return self.quality > 0.0

    def is_negative(self) -> bool:
        """Check if outcome is negative."""
        return self.quality < 0.0


@dataclass(frozen=True)
class SalienceUpdate:
    """A salience adjustment to be applied to a memory."""

    memory_id: UUID
    trace_id: UUID
    delta: float  # Positive = increase, negative = decrease
    reason: str  # "positive_outcome", "negative_outcome"

    @classmethod
    def from_outcome(
        cls,
        memory_id: UUID,
        trace_id: UUID,
        outcome: Outcome,
        contribution: float,
    ) -> "SalienceUpdate":
        """Create salience update from outcome.

        Args:
            memory_id: The memory to update
            trace_id: The decision trace
            outcome: The observed outcome
            contribution: How much this memory contributed (0.0 - 1.0)
        """
        # Scale delta by both outcome quality and contribution
        # Max adjustment is 0.1 per outcome to prevent wild swings
        delta = outcome.quality * contribution * 0.1

        reason = "positive_outcome" if outcome.quality > 0 else "negative_outcome"

        return cls(
            memory_id=memory_id,
            trace_id=trace_id,
            delta=delta,
            reason=reason,
        )
