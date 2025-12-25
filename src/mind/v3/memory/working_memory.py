"""
Working memory for Mind v3.

Implements short-term memory storage with:
- Capacity limits (Miller's law: 7 +/- 2)
- Activation-based priority
- Time-based decay
- Access-based reinforcement
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Sequence


class MemoryType(str, Enum):
    """Types of memory items."""

    EVENT = "event"           # Raw events from transcripts
    DECISION = "decision"     # Decisions made
    LEARNING = "learning"     # Things learned
    PATTERN = "pattern"       # Detected patterns
    REMINDER = "reminder"     # Future intentions


@dataclass
class MemoryItem:
    """A single memory item."""

    id: str
    content: str
    memory_type: MemoryType
    activation: float = 1.0   # Current activation level (0-1)
    importance: float = 0.5   # Base importance (0-1)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkingMemoryConfig:
    """Configuration for working memory."""

    # Capacity (Miller's law: 7 +/- 2)
    capacity: int = 7

    # Time-to-live for items (seconds)
    default_ttl_seconds: int = 3600  # 1 hour

    # Activation bounds
    min_activation: float = 0.0
    max_activation: float = 1.0

    # Access boost amount
    access_boost: float = 0.1

    # Decay rate per decay() call
    base_decay_rate: float = 0.1


class WorkingMemory:
    """
    Working memory with capacity limits and activation dynamics.

    Implements:
    - Limited capacity (evicts low-priority items)
    - Activation-based priority (recent/important items stay)
    - Decay over time (unused items lose activation)
    - Reinforcement on access (used items stay stronger)
    """

    def __init__(self, config: WorkingMemoryConfig | None = None):
        """
        Initialize working memory.

        Args:
            config: Memory configuration
        """
        self.config = config or WorkingMemoryConfig()
        self._items: dict[str, MemoryItem] = {}

    @property
    def size(self) -> int:
        """Get number of items in memory."""
        return len(self._items)

    def add(self, item: MemoryItem) -> None:
        """
        Add item to working memory.

        If capacity is exceeded, lowest priority item is evicted.

        Args:
            item: Memory item to add
        """
        # Update existing or add new
        self._items[item.id] = item

        # Evict if over capacity
        self._evict_if_needed()

    def get(self, item_id: str) -> MemoryItem | None:
        """
        Get item by ID, boosting its activation.

        Args:
            item_id: ID of item to retrieve

        Returns:
            Memory item or None
        """
        item = self._items.get(item_id)

        if item is not None:
            # Boost activation on access
            item.activation = min(
                self.config.max_activation,
                item.activation + self.config.access_boost
            )
            item.accessed_at = datetime.now()

        return item

    def peek(self, item_id: str) -> MemoryItem | None:
        """
        Get item by ID without boosting activation.

        Use this for inspection without affecting memory dynamics.

        Args:
            item_id: ID of item to retrieve

        Returns:
            Memory item or None
        """
        return self._items.get(item_id)

    def remove(self, item_id: str) -> bool:
        """
        Remove item from memory.

        Args:
            item_id: ID of item to remove

        Returns:
            True if item was removed
        """
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    def clear(self) -> None:
        """Remove all items from memory."""
        self._items.clear()

    def list(
        self,
        memory_type: MemoryType | None = None,
    ) -> list[MemoryItem]:
        """
        List items in memory.

        Args:
            memory_type: Optional filter by type

        Returns:
            List of memory items
        """
        items = list(self._items.values())

        if memory_type is not None:
            items = [i for i in items if i.memory_type == memory_type]

        # Sort by activation (highest first)
        items.sort(key=lambda x: x.activation, reverse=True)

        return items

    def decay(self, decay_factor: float | None = None) -> None:
        """
        Apply decay to all items.

        Higher importance items decay slower.

        Args:
            decay_factor: Decay amount (defaults to config)
        """
        factor = decay_factor if decay_factor is not None else self.config.base_decay_rate

        for item in self._items.values():
            # Important items decay slower
            effective_decay = factor * (1 - item.importance)
            item.activation = max(
                self.config.min_activation,
                item.activation - effective_decay
            )

    def reinforce(self, item_id: str, amount: float) -> bool:
        """
        Reinforce an item's activation.

        Args:
            item_id: ID of item to reinforce
            amount: Amount to add to activation

        Returns:
            True if item was found and reinforced
        """
        item = self._items.get(item_id)

        if item is None:
            return False

        item.activation = min(
            self.config.max_activation,
            item.activation + amount
        )

        return True

    def snapshot(self) -> list[dict[str, Any]]:
        """
        Create snapshot of current memory state.

        Returns:
            List of serialized items
        """
        return [
            {
                "id": item.id,
                "content": item.content,
                "memory_type": item.memory_type.value,
                "activation": item.activation,
                "importance": item.importance,
                "created_at": item.created_at.isoformat(),
                "accessed_at": item.accessed_at.isoformat(),
                "metadata": item.metadata,
            }
            for item in self._items.values()
        ]

    def restore(self, snapshot: Sequence[dict[str, Any]]) -> None:
        """
        Restore memory state from snapshot.

        Args:
            snapshot: Previously created snapshot
        """
        self._items.clear()

        for data in snapshot:
            item = MemoryItem(
                id=data["id"],
                content=data["content"],
                memory_type=MemoryType(data["memory_type"]),
                activation=data["activation"],
                importance=data["importance"],
                created_at=datetime.fromisoformat(data["created_at"]),
                accessed_at=datetime.fromisoformat(data["accessed_at"]),
                metadata=data.get("metadata", {}),
            )
            self._items[item.id] = item

    def _evict_if_needed(self) -> None:
        """Evict lowest priority items if over capacity."""
        while len(self._items) > self.config.capacity:
            # Find item with lowest priority score
            min_score = float("inf")
            min_id = None

            for item_id, item in self._items.items():
                # Priority = activation * importance
                score = item.activation * (0.5 + item.importance * 0.5)
                if score < min_score:
                    min_score = score
                    min_id = item_id

            if min_id is not None:
                del self._items[min_id]
            else:
                break
