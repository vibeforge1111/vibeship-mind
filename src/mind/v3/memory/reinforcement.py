"""
Memory reinforcement system for Mind v3.

Implements learning through use:
- Retrieval strengthens memories
- Positive/negative feedback adjusts activation
- Prediction confirmation boosts confidence
- Tracks reinforcement history for analysis
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .working_memory import MemoryItem


class FeedbackType(str, Enum):
    """Types of reinforcement feedback."""

    RETRIEVAL = "retrieval"       # Memory was retrieved
    POSITIVE = "positive"         # User confirmed/liked
    NEGATIVE = "negative"         # User rejected/disliked
    CORRECTION = "correction"     # User provided correction
    CONFIRMED = "confirmed"       # Prediction was correct
    FAILED = "failed"             # Prediction was wrong


@dataclass
class ReinforcementEvent:
    """A single reinforcement event."""

    item_id: str
    feedback_type: FeedbackType
    amount: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class ReinforcementConfig:
    """Configuration for reinforcement system."""

    # Boost amounts
    retrieval_boost: float = 0.1
    positive_boost: float = 0.2
    negative_penalty: float = 0.1
    confirmation_boost: float = 0.1
    failure_penalty: float = 0.1

    # Bounds
    max_activation: float = 1.0
    min_activation: float = 0.0
    max_importance: float = 1.0
    min_importance: float = 0.0

    # Tracking
    track_history: bool = False


class ReinforcementManager:
    """
    Manages memory reinforcement through use.

    Memories get stronger when:
    - Retrieved (accessed)
    - Confirmed (prediction correct)
    - Positive feedback received

    Memories get weaker when:
    - Negative feedback received
    - Prediction failed
    """

    def __init__(self, config: ReinforcementConfig | None = None):
        """
        Initialize reinforcement manager.

        Args:
            config: Reinforcement configuration
        """
        self.config = config or ReinforcementConfig()
        self._history: dict[str, list[ReinforcementEvent]] = defaultdict(list)

    def on_retrieval(self, item: MemoryItem) -> MemoryItem:
        """
        Reinforce item on retrieval.

        Args:
            item: Retrieved memory item

        Returns:
            Item with boosted activation
        """
        event = ReinforcementEvent(
            item_id=item.id,
            feedback_type=FeedbackType.RETRIEVAL,
            amount=self.config.retrieval_boost,
        )

        return self.apply(item, event)

    def on_positive_feedback(self, item: MemoryItem) -> MemoryItem:
        """
        Reinforce item on positive feedback.

        Args:
            item: Memory item that received positive feedback

        Returns:
            Item with boosted activation
        """
        event = ReinforcementEvent(
            item_id=item.id,
            feedback_type=FeedbackType.POSITIVE,
            amount=self.config.positive_boost,
        )

        return self.apply(item, event)

    def on_negative_feedback(self, item: MemoryItem) -> MemoryItem:
        """
        Penalize item on negative feedback.

        Args:
            item: Memory item that received negative feedback

        Returns:
            Item with reduced activation
        """
        event = ReinforcementEvent(
            item_id=item.id,
            feedback_type=FeedbackType.NEGATIVE,
            amount=-self.config.negative_penalty,
        )

        return self.apply(item, event)

    def on_prediction_confirmed(self, item: MemoryItem) -> MemoryItem:
        """
        Boost importance when prediction confirmed.

        Args:
            item: Pattern/memory whose prediction was correct

        Returns:
            Item with boosted importance
        """
        event = ReinforcementEvent(
            item_id=item.id,
            feedback_type=FeedbackType.CONFIRMED,
            amount=self.config.confirmation_boost,
        )

        if self.config.track_history:
            self._history[item.id].append(event)

        new_importance = min(
            self.config.max_importance,
            item.importance + event.amount
        )

        return MemoryItem(
            id=item.id,
            content=item.content,
            memory_type=item.memory_type,
            activation=item.activation,
            importance=new_importance,
            created_at=item.created_at,
            accessed_at=datetime.now(),
            metadata=item.metadata,
        )

    def on_prediction_failed(self, item: MemoryItem) -> MemoryItem:
        """
        Reduce importance when prediction failed.

        Args:
            item: Pattern/memory whose prediction was wrong

        Returns:
            Item with reduced importance
        """
        event = ReinforcementEvent(
            item_id=item.id,
            feedback_type=FeedbackType.FAILED,
            amount=-self.config.failure_penalty,
        )

        if self.config.track_history:
            self._history[item.id].append(event)

        new_importance = max(
            self.config.min_importance,
            item.importance + event.amount
        )

        return MemoryItem(
            id=item.id,
            content=item.content,
            memory_type=item.memory_type,
            activation=item.activation,
            importance=new_importance,
            created_at=item.created_at,
            accessed_at=datetime.now(),
            metadata=item.metadata,
        )

    def apply(
        self,
        item: MemoryItem,
        event: ReinforcementEvent,
    ) -> MemoryItem:
        """
        Apply a reinforcement event to an item.

        Args:
            item: Memory item to reinforce
            event: Reinforcement event to apply

        Returns:
            Item with adjusted activation
        """
        if self.config.track_history:
            self._history[item.id].append(event)

        # Calculate new activation
        new_activation = item.activation + event.amount
        new_activation = max(self.config.min_activation, new_activation)
        new_activation = min(self.config.max_activation, new_activation)

        return MemoryItem(
            id=item.id,
            content=item.content,
            memory_type=item.memory_type,
            activation=new_activation,
            importance=item.importance,
            created_at=item.created_at,
            accessed_at=datetime.now(),
            metadata=item.metadata,
        )

    def get_history(self, item_id: str) -> list[ReinforcementEvent]:
        """
        Get reinforcement history for an item.

        Args:
            item_id: ID of item

        Returns:
            List of reinforcement events
        """
        return list(self._history.get(item_id, []))

    def get_stats(self, item_id: str) -> dict:
        """
        Get reinforcement statistics for an item.

        Args:
            item_id: ID of item

        Returns:
            Statistics dict
        """
        history = self._history.get(item_id, [])

        retrieval_count = sum(
            1 for e in history if e.feedback_type == FeedbackType.RETRIEVAL
        )
        positive_count = sum(
            1 for e in history if e.feedback_type == FeedbackType.POSITIVE
        )
        negative_count = sum(
            1 for e in history if e.feedback_type == FeedbackType.NEGATIVE
        )

        net = sum(e.amount for e in history)

        return {
            "retrieval_count": retrieval_count,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "total_events": len(history),
            "net_reinforcement": net,
        }
