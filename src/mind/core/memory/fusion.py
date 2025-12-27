"""Reciprocal Rank Fusion (RRF) for multi-source retrieval.

RRF combines rankings from multiple retrieval sources into a single
fused ranking. It's robust and doesn't require score normalization.

Formula: RRF_score(d) = Σ 1 / (k + rank_i(d))

Where:
- d is a document (memory)
- k is a constant (typically 60)
- rank_i(d) is the rank of d in the i-th retrieval source

Reference: Cormack et al., "Reciprocal Rank Fusion outperforms
Condorcet and individual Rank Learning Methods" (SIGIR 2009)
"""

from dataclasses import dataclass
from uuid import UUID

from mind.core.memory.models import Memory


@dataclass
class RankedMemory:
    """A memory with its rank from a specific source."""

    memory: Memory
    rank: int
    source: str
    raw_score: float | None = None


@dataclass
class FusedMemory:
    """A memory with its fused RRF score."""

    memory: Memory
    rrf_score: float
    sources: dict[str, int]  # source -> rank
    raw_scores: dict[str, float]  # source -> score

    @property
    def source_count(self) -> int:
        """Number of sources this memory appeared in."""
        return len(self.sources)


def reciprocal_rank_fusion(
    ranked_lists: list[list[RankedMemory]],
    k: int = 60,
    limit: int | None = None,
) -> list[FusedMemory]:
    """Fuse multiple ranked lists using RRF.

    Args:
        ranked_lists: List of ranked memory lists from different sources
        k: RRF constant (higher = more weight to lower ranks)
        limit: Maximum results to return

    Returns:
        Fused list sorted by RRF score descending
    """
    # Aggregate scores by memory ID
    scores: dict[UUID, float] = {}
    sources: dict[UUID, dict[str, int]] = {}
    raw_scores: dict[UUID, dict[str, float]] = {}
    memories: dict[UUID, Memory] = {}

    for ranked_list in ranked_lists:
        for ranked in ranked_list:
            mid = ranked.memory.memory_id

            # Store memory reference
            memories[mid] = ranked.memory

            # Calculate RRF contribution
            rrf_contribution = 1.0 / (k + ranked.rank)
            scores[mid] = scores.get(mid, 0.0) + rrf_contribution

            # Track sources
            if mid not in sources:
                sources[mid] = {}
                raw_scores[mid] = {}
            sources[mid][ranked.source] = ranked.rank
            if ranked.raw_score is not None:
                raw_scores[mid][ranked.source] = ranked.raw_score

    # Sort by RRF score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    # Build result
    results = []
    for mid in sorted_ids:
        results.append(
            FusedMemory(
                memory=memories[mid],
                rrf_score=scores[mid],
                sources=sources[mid],
                raw_scores=raw_scores[mid],
            )
        )

    if limit:
        results = results[:limit]

    return results


def weighted_rrf(
    ranked_lists: list[tuple[list[RankedMemory], float]],
    k: int = 60,
    limit: int | None = None,
) -> list[FusedMemory]:
    """Fuse with source weights.

    Args:
        ranked_lists: List of (ranked_list, weight) tuples
        k: RRF constant
        limit: Maximum results

    Returns:
        Fused list with weighted scores
    """
    scores: dict[UUID, float] = {}
    sources: dict[UUID, dict[str, int]] = {}
    raw_scores: dict[UUID, dict[str, float]] = {}
    memories: dict[UUID, Memory] = {}

    for ranked_list, weight in ranked_lists:
        for ranked in ranked_list:
            mid = ranked.memory.memory_id
            memories[mid] = ranked.memory

            # Weighted RRF contribution
            rrf_contribution = weight / (k + ranked.rank)
            scores[mid] = scores.get(mid, 0.0) + rrf_contribution

            if mid not in sources:
                sources[mid] = {}
                raw_scores[mid] = {}
            sources[mid][ranked.source] = ranked.rank
            if ranked.raw_score is not None:
                raw_scores[mid][ranked.source] = ranked.raw_score

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    results = []
    for mid in sorted_ids:
        results.append(
            FusedMemory(
                memory=memories[mid],
                rrf_score=scores[mid],
                sources=sources[mid],
                raw_scores=raw_scores[mid],
            )
        )

    if limit:
        results = results[:limit]

    return results
