"""
Intelligence levels configuration for Mind v3.

Defines the different intelligence levels that control which Claude models
are used for extraction, reranking, and summary operations.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntelligenceLevel:
    """
    Configuration for a specific intelligence level.

    Attributes:
        name: Level identifier (FREE, LITE, BALANCED, PRO, ULTRA).
        description: Human-readable description of the level.
        extraction_model: Model for memory extraction (None = local only).
        reranking_model: Model for search result reranking.
        summary_model: Model for session summaries.
        estimated_cost: Estimated monthly cost string.
    """

    name: str
    description: str
    extraction_model: str | None  # None = local only
    reranking_model: str | None
    summary_model: str | None
    estimated_cost: str


# Intelligence levels from FREE to ULTRA
LEVELS: dict[str, IntelligenceLevel] = {
    "FREE": IntelligenceLevel(
        name="FREE",
        description="No API calls - local extraction only",
        extraction_model=None,
        reranking_model=None,
        summary_model=None,
        estimated_cost="$0/mo",
    ),
    "LITE": IntelligenceLevel(
        name="LITE",
        description="Basic API extraction with Haiku",
        extraction_model="haiku",
        reranking_model=None,
        summary_model=None,
        estimated_cost="~$2/mo",
    ),
    "BALANCED": IntelligenceLevel(
        name="BALANCED",
        description="Extraction and reranking with Haiku, summaries with Sonnet",
        extraction_model="haiku",
        reranking_model="haiku",
        summary_model="sonnet",
        estimated_cost="~$15/mo",
    ),
    "PRO": IntelligenceLevel(
        name="PRO",
        description="All features with Sonnet for reranking and summaries",
        extraction_model="haiku",
        reranking_model="sonnet",
        summary_model="sonnet",
        estimated_cost="~$40/mo",
    ),
    "ULTRA": IntelligenceLevel(
        name="ULTRA",
        description="Maximum quality with Sonnet extraction and Opus for everything else",
        extraction_model="sonnet",
        reranking_model="opus",
        summary_model="opus",
        estimated_cost="~$150/mo",
    ),
}


def get_level(name: str) -> IntelligenceLevel:
    """
    Get an IntelligenceLevel by name.

    Args:
        name: Level name (case-insensitive).

    Returns:
        IntelligenceLevel for the given name, or FREE level for invalid names.
    """
    normalized = name.strip().upper()
    return LEVELS.get(normalized, LEVELS["FREE"])
