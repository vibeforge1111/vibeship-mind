"""Memory retrieval types and logic."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from mind.core.memory.models import Memory, TemporalLevel


@dataclass(frozen=True)
class RetrievalRequest:
    """Request to retrieve memories."""

    user_id: UUID
    query: str
    limit: int = 10
    temporal_levels: list[TemporalLevel] | None = None  # None = all levels
    min_salience: float = 0.0
    include_expired: bool = False


@dataclass(frozen=True)
class ScoredMemory:
    """A memory with retrieval scores."""

    memory: Memory
    vector_score: float | None = None  # Semantic similarity
    keyword_score: float | None = None  # BM25 score
    recency_score: float | None = None  # Time decay
    salience_score: float | None = None  # Outcome-weighted salience
    final_score: float = 0.0  # Combined RRF score
    rank: int = 0

    @property
    def source(self) -> str:
        """Primary source of this retrieval."""
        if self.vector_score and self.vector_score > 0.5:
            return "vector"
        if self.keyword_score and self.keyword_score > 0.5:
            return "keyword"
        return "fusion"


@dataclass
class RetrievalResult:
    """Result of a memory retrieval operation."""

    retrieval_id: UUID = field(default_factory=uuid4)
    memories: list[ScoredMemory] = field(default_factory=list)
    query: str = ""
    latency_ms: float = 0.0

    # For decision tracking
    trace_id: UUID | None = None

    @property
    def memory_ids(self) -> list[UUID]:
        """Get list of memory IDs in rank order."""
        return [sm.memory.memory_id for sm in self.memories]

    @property
    def top_memory(self) -> ScoredMemory | None:
        """Get the highest-ranked memory."""
        return self.memories[0] if self.memories else None

    def for_decision_trace(self) -> dict[str, float]:
        """Get memory scores for decision tracking."""
        return {str(sm.memory.memory_id): sm.final_score for sm in self.memories}
