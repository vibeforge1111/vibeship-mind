"""
Model cascade for Mind v3 intelligence layer.

Routes extraction tasks through a tiered model cascade:
- Tier 1: Local (regex, heuristics) - free, instant
- Tier 2: Fast API (Haiku, GPT-4o-mini) - cheap, quick
- Tier 3: Powerful API (Sonnet, Opus) - smart, periodic

Each tier can escalate to the next if confidence is too low.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class ModelTier(str, Enum):
    """Model tiers in the cascade, ordered by capability."""

    LOCAL = "local"
    FAST_API = "fast_api"
    POWERFUL_API = "powerful_api"


@dataclass
class CascadeConfig:
    """Configuration for model cascade behavior."""

    # Which tiers are enabled
    enable_local: bool = True
    enable_fast_api: bool = False  # Requires API key
    enable_powerful_api: bool = False  # Requires API key

    # Confidence thresholds for escalation
    local_confidence_threshold: float = 0.7
    fast_api_confidence_threshold: float = 0.85

    # Model preferences per tier
    local_model: str = "regex"  # Built-in regex/heuristics
    fast_api_model: str = "haiku"  # Claude Haiku or similar
    powerful_api_model: str = "sonnet"  # Claude Sonnet or similar


@dataclass
class ExtractionResult:
    """Result from an extraction operation."""

    content: dict[str, Any]
    confidence: float
    tier_used: ModelTier
    model_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Extractor(Protocol):
    """Protocol for extractors that can be registered with the cascade."""

    def extract(self, text: str) -> ExtractionResult:
        """Extract information from text."""
        ...


class ModelCascade:
    """
    Routes extraction through tiered models based on confidence.

    Starts with the cheapest/fastest tier and escalates to more
    capable tiers only when confidence is below threshold.
    """

    def __init__(self, config: CascadeConfig | None = None):
        """
        Initialize model cascade.

        Args:
            config: Cascade configuration. Uses defaults if not provided.
        """
        self.config = config or CascadeConfig()
        self.extractors: dict[ModelTier, Extractor] = {}

    def register_extractor(self, tier: ModelTier, extractor: Extractor) -> None:
        """
        Register an extractor for a specific tier.

        Args:
            tier: The model tier this extractor handles
            extractor: The extractor implementation
        """
        self.extractors[tier] = extractor

    def get_available_tiers(self) -> list[ModelTier]:
        """Get list of enabled tiers in order."""
        tiers = []

        if self.config.enable_local:
            tiers.append(ModelTier.LOCAL)
        if self.config.enable_fast_api:
            tiers.append(ModelTier.FAST_API)
        if self.config.enable_powerful_api:
            tiers.append(ModelTier.POWERFUL_API)

        return tiers

    def get_confidence_threshold(self, tier: ModelTier) -> float:
        """Get the confidence threshold for a tier."""
        if tier == ModelTier.LOCAL:
            return self.config.local_confidence_threshold
        elif tier == ModelTier.FAST_API:
            return self.config.fast_api_confidence_threshold
        else:
            return 1.0  # No threshold for highest tier

    def should_escalate(self, result: ExtractionResult) -> bool:
        """
        Determine if result should escalate to next tier.

        Args:
            result: The extraction result to evaluate

        Returns:
            True if should escalate, False otherwise
        """
        # Can't escalate if already at highest available tier
        next_tier = self.get_next_tier(result.tier_used)
        if next_tier is None:
            return False

        # Escalate if confidence is below threshold
        threshold = self.get_confidence_threshold(result.tier_used)
        return result.confidence < threshold

    def get_next_tier(self, current_tier: ModelTier) -> ModelTier | None:
        """
        Get the next available tier after current.

        Args:
            current_tier: The current tier

        Returns:
            Next tier or None if at highest
        """
        available = self.get_available_tiers()

        try:
            current_idx = available.index(current_tier)
            if current_idx + 1 < len(available):
                return available[current_idx + 1]
        except ValueError:
            pass

        return None

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract information using the cascade.

        Starts at lowest tier and escalates based on confidence.

        Args:
            text: Text to extract from

        Returns:
            Best extraction result from cascade
        """
        available_tiers = self.get_available_tiers()

        if not available_tiers:
            return ExtractionResult(
                content={},
                confidence=0.0,
                tier_used=ModelTier.LOCAL,
                model_name="none",
                metadata={"error": "No tiers available"},
            )

        # Start with first available tier
        current_tier = available_tiers[0]
        result = self._extract_at_tier(text, current_tier)

        # Escalate while confidence is low and more tiers available
        while self.should_escalate(result):
            next_tier = self.get_next_tier(result.tier_used)
            if next_tier is None:
                break

            result = self._extract_at_tier(text, next_tier)

        return result

    def _extract_at_tier(self, text: str, tier: ModelTier) -> ExtractionResult:
        """
        Extract using a specific tier's extractor.

        Args:
            text: Text to extract from
            tier: Tier to use

        Returns:
            Extraction result
        """
        extractor = self.extractors.get(tier)

        if extractor is None:
            return ExtractionResult(
                content={},
                confidence=0.0,
                tier_used=tier,
                model_name="none",
                metadata={"error": f"No extractor registered for {tier.value}"},
            )

        return extractor.extract(text)
