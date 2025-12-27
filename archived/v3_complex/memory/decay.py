"""
Memory decay system for Mind v3.

Implements time-based activation decay with:
- Multiple decay curves (exponential, linear, power law)
- Importance-modulated decay rates
- Archival thresholds
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .working_memory import MemoryItem


class DecayCurve(str, Enum):
    """Types of decay curves."""

    LINEAR = "linear"        # Constant rate decay
    EXPONENTIAL = "exponential"  # Half-life based decay
    POWER_LAW = "power_law"  # Slower initial, faster later


@dataclass
class DecayConfig:
    """Configuration for decay system."""

    # Decay curve type
    curve: DecayCurve = DecayCurve.EXPONENTIAL

    # Half-life in hours (time for activation to halve)
    half_life_hours: float = 24

    # Minimum activation (never decays below this)
    min_activation: float = 0.01

    # Importance factor (0-1, how much importance affects decay)
    importance_factor: float = 0.5

    # Threshold for archival
    archive_threshold: float = 0.05


class DecayManager:
    """
    Manages memory activation decay.

    Applies configurable decay curves to memory items based
    on time since last access. Important items decay slower.
    """

    def __init__(self, config: DecayConfig | None = None):
        """
        Initialize decay manager.

        Args:
            config: Decay configuration
        """
        self.config = config or DecayConfig()

    def calculate_decay(
        self,
        initial_activation: float,
        hours_elapsed: float,
        importance: float = 0.5,
    ) -> float:
        """
        Calculate decayed activation value.

        Args:
            initial_activation: Starting activation level
            hours_elapsed: Hours since last access
            importance: Item importance (modulates decay rate)

        Returns:
            Decayed activation value
        """
        if hours_elapsed <= 0:
            return initial_activation

        # Adjust half-life based on importance
        # Higher importance = longer half-life = slower decay
        importance_multiplier = 1 + (importance * self.config.importance_factor)
        effective_half_life = self.config.half_life_hours * importance_multiplier

        if self.config.curve == DecayCurve.EXPONENTIAL:
            decayed = self._exponential_decay(
                initial_activation, hours_elapsed, effective_half_life
            )
        elif self.config.curve == DecayCurve.LINEAR:
            decayed = self._linear_decay(
                initial_activation, hours_elapsed, effective_half_life
            )
        elif self.config.curve == DecayCurve.POWER_LAW:
            decayed = self._power_law_decay(
                initial_activation, hours_elapsed, effective_half_life
            )
        else:
            decayed = initial_activation

        # Apply minimum
        return max(self.config.min_activation, decayed)

    def _exponential_decay(
        self,
        initial: float,
        hours: float,
        half_life: float,
    ) -> float:
        """Exponential decay: A(t) = A0 * 0.5^(t/half_life)"""
        return initial * math.pow(0.5, hours / half_life)

    def _linear_decay(
        self,
        initial: float,
        hours: float,
        half_life: float,
    ) -> float:
        """Linear decay: loses half the initial value in half_life hours."""
        decay_rate = initial / (2 * half_life)
        return max(0, initial - (decay_rate * hours))

    def _power_law_decay(
        self,
        initial: float,
        hours: float,
        half_life: float,
    ) -> float:
        """Power law decay: A(t) = A0 / (1 + t/scale)^power"""
        # Calibrate so that at half_life, we get ~0.5 * initial
        scale = half_life / (math.pow(2, 1) - 1)  # ~24 for half_life=24
        return initial / math.pow(1 + hours / scale, 1)

    def apply_decay(self, item: MemoryItem) -> MemoryItem:
        """
        Apply decay to a memory item based on time since access.

        Args:
            item: Memory item to decay

        Returns:
            New MemoryItem with decayed activation
        """
        now = datetime.now()
        hours_elapsed = (now - item.accessed_at).total_seconds() / 3600

        new_activation = self.calculate_decay(
            initial_activation=item.activation,
            hours_elapsed=hours_elapsed,
            importance=item.importance,
        )

        # Return new item with updated activation
        return MemoryItem(
            id=item.id,
            content=item.content,
            memory_type=item.memory_type,
            activation=new_activation,
            importance=item.importance,
            created_at=item.created_at,
            accessed_at=item.accessed_at,
            metadata=item.metadata,
        )

    def apply_decay_batch(self, items: list[MemoryItem]) -> list[MemoryItem]:
        """
        Apply decay to multiple items.

        Args:
            items: Memory items to decay

        Returns:
            List of decayed items
        """
        return [self.apply_decay(item) for item in items]

    def should_archive(self, item: MemoryItem) -> bool:
        """
        Check if item should be archived.

        Args:
            item: Memory item to check

        Returns:
            True if activation is below archive threshold
        """
        return item.activation < self.config.archive_threshold

    def hours_until_archive(self, item: MemoryItem) -> float:
        """
        Estimate hours until item reaches archive threshold.

        Args:
            item: Memory item to check

        Returns:
            Estimated hours until archival
        """
        if item.activation <= self.config.archive_threshold:
            return 0

        # For exponential decay: solve for t where A0 * 0.5^(t/hl) = threshold
        # t = hl * log2(A0 / threshold)
        if self.config.curve == DecayCurve.EXPONENTIAL:
            importance_multiplier = 1 + (item.importance * self.config.importance_factor)
            effective_half_life = self.config.half_life_hours * importance_multiplier

            ratio = item.activation / self.config.archive_threshold
            return effective_half_life * math.log2(ratio)

        # For other curves, use approximation
        # Estimate by running simulation
        hours = 0
        activation = item.activation
        step = 1.0  # 1 hour steps

        while activation > self.config.archive_threshold and hours < 10000:
            hours += step
            activation = self.calculate_decay(
                item.activation,
                hours,
                item.importance,
            )

        return hours
