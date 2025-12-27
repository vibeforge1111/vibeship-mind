"""Memory retrieval service with multi-source fusion."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from mind.core.errors import Result
from mind.core.memory.models import Memory, TemporalLevel
from mind.core.memory.retrieval import RetrievalRequest, RetrievalResult, ScoredMemory
from mind.core.memory.fusion import (
    RankedMemory,
    FusedMemory,
    reciprocal_rank_fusion,
    weighted_rrf,
)
from mind.infrastructure.postgres.models import MemoryModel
from mind.infrastructure.embeddings.openai import OpenAIEmbedder

logger = structlog.get_logger()


class RetrievalService:
    """Multi-source memory retrieval with RRF fusion.

    Combines:
    - Vector similarity (semantic search)
    - Keyword/BM25 (full-text search)
    - Salience ranking (outcome-weighted)
    - Recency decay (time-based)
    """

    # Source weights for weighted RRF
    WEIGHTS = {
        "vector": 1.0,     # Semantic similarity
        "keyword": 0.8,    # Full-text match
        "salience": 0.6,   # Outcome-weighted importance
        "recency": 0.4,    # Time decay
    }

    def __init__(
        self,
        session: AsyncSession,
        embedder: OpenAIEmbedder | None = None,
    ):
        self._session = session
        self._embedder = embedder

    async def retrieve(
        self,
        request: RetrievalRequest,
    ) -> Result[RetrievalResult]:
        """Retrieve memories using multi-source fusion.

        Args:
            request: Retrieval parameters

        Returns:
            Result with fused retrieval results
        """
        start_time = datetime.now(UTC)
        log = logger.bind(
            user_id=str(request.user_id),
            query_length=len(request.query),
            limit=request.limit,
        )

        # Run retrieval sources in parallel
        sources_to_run = []

        # Vector search (if embedder available)
        if self._embedder:
            sources_to_run.append(self._vector_search(request))

        # Keyword search (always available)
        sources_to_run.append(self._keyword_search(request))

        # Salience ranking (always available)
        sources_to_run.append(self._salience_search(request))

        # Recency ranking (always available)
        sources_to_run.append(self._recency_search(request))

        # Execute in parallel
        results = await asyncio.gather(*sources_to_run, return_exceptions=True)

        # Collect successful results
        ranked_lists: list[tuple[list[RankedMemory], float]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.warning("retrieval_source_failed", source=i, error=str(result))
                continue
            if result:
                source_name = result[0].source if result else "unknown"
                weight = self.WEIGHTS.get(source_name, 1.0)
                ranked_lists.append((result, weight))

        if not ranked_lists:
            log.warning("no_retrieval_results")
            return Result.ok(
                RetrievalResult(
                    retrieval_id=uuid4(),
                    memories=[],
                    query=request.query,
                    latency_ms=0,
                )
            )

        # Fuse results
        fused = weighted_rrf(
            ranked_lists=ranked_lists,
            k=60,
            limit=request.limit,
        )

        # Convert to ScoredMemory
        scored_memories = []
        for i, fm in enumerate(fused):
            scored = ScoredMemory(
                memory=fm.memory,
                vector_score=fm.raw_scores.get("vector"),
                keyword_score=fm.raw_scores.get("keyword"),
                recency_score=fm.raw_scores.get("recency"),
                salience_score=fm.raw_scores.get("salience"),
                final_score=fm.rrf_score,
                rank=i + 1,
            )
            scored_memories.append(scored)

        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        log.info(
            "retrieval_complete",
            result_count=len(scored_memories),
            sources=len(ranked_lists),
            latency_ms=round(latency_ms, 2),
        )

        return Result.ok(
            RetrievalResult(
                retrieval_id=uuid4(),
                memories=scored_memories,
                query=request.query,
                latency_ms=latency_ms,
            )
        )

    async def _vector_search(
        self,
        request: RetrievalRequest,
    ) -> list[RankedMemory]:
        """Search by vector similarity."""
        if not self._embedder:
            return []

        # Generate query embedding
        embed_result = await self._embedder.embed(request.query)
        if embed_result.is_err:
            logger.warning("embedding_failed", error=str(embed_result.error))
            return []

        query_embedding = embed_result.value

        # Vector search using pgvector
        stmt = text("""
            SELECT
                memory_id, user_id, content, content_type, temporal_level,
                valid_from, valid_until, base_salience, outcome_adjustment,
                retrieval_count, decision_count, positive_outcomes, negative_outcomes,
                promoted_from_level, promotion_timestamp, created_at, updated_at,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM memories
            WHERE user_id = :user_id
                AND embedding IS NOT NULL
                AND (valid_until IS NULL OR valid_until > :now)
                AND valid_from <= :now
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)

        result = await self._session.execute(
            stmt,
            {
                "user_id": str(request.user_id),
                "embedding": query_embedding,
                "now": datetime.now(UTC),
                "limit": request.limit * 2,  # Over-fetch for fusion
            },
        )

        ranked = []
        for i, row in enumerate(result.fetchall()):
            memory = self._row_to_memory(row)
            ranked.append(
                RankedMemory(
                    memory=memory,
                    rank=i + 1,
                    source="vector",
                    raw_score=float(row.similarity),
                )
            )

        return ranked

    async def _keyword_search(
        self,
        request: RetrievalRequest,
    ) -> list[RankedMemory]:
        """Search by keyword/full-text."""
        # PostgreSQL full-text search
        stmt = text("""
            SELECT
                memory_id, user_id, content, content_type, temporal_level,
                valid_from, valid_until, base_salience, outcome_adjustment,
                retrieval_count, decision_count, positive_outcomes, negative_outcomes,
                promoted_from_level, promotion_timestamp, created_at, updated_at,
                ts_rank(to_tsvector('english', content), plainto_tsquery('english', :query)) as rank_score
            FROM memories
            WHERE user_id = :user_id
                AND to_tsvector('english', content) @@ plainto_tsquery('english', :query)
                AND (valid_until IS NULL OR valid_until > :now)
                AND valid_from <= :now
            ORDER BY rank_score DESC
            LIMIT :limit
        """)

        result = await self._session.execute(
            stmt,
            {
                "user_id": str(request.user_id),
                "query": request.query,
                "now": datetime.now(UTC),
                "limit": request.limit * 2,
            },
        )

        ranked = []
        for i, row in enumerate(result.fetchall()):
            memory = self._row_to_memory(row)
            ranked.append(
                RankedMemory(
                    memory=memory,
                    rank=i + 1,
                    source="keyword",
                    raw_score=float(row.rank_score) if row.rank_score else 0.0,
                )
            )

        return ranked

    async def _salience_search(
        self,
        request: RetrievalRequest,
    ) -> list[RankedMemory]:
        """Search by outcome-weighted salience."""
        stmt = (
            select(MemoryModel)
            .where(MemoryModel.user_id == request.user_id)
            .where(
                (MemoryModel.valid_until.is_(None))
                | (MemoryModel.valid_until > datetime.now(UTC))
            )
            .where(MemoryModel.valid_from <= datetime.now(UTC))
            .order_by(
                (MemoryModel.base_salience + MemoryModel.outcome_adjustment).desc()
            )
            .limit(request.limit * 2)
        )

        if request.temporal_levels:
            levels = [level.value for level in request.temporal_levels]
            stmt = stmt.where(MemoryModel.temporal_level.in_(levels))

        if request.min_salience > 0:
            stmt = stmt.where(
                (MemoryModel.base_salience + MemoryModel.outcome_adjustment)
                >= request.min_salience
            )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        ranked = []
        for i, model in enumerate(models):
            memory = self._model_to_memory(model)
            ranked.append(
                RankedMemory(
                    memory=memory,
                    rank=i + 1,
                    source="salience",
                    raw_score=memory.effective_salience,
                )
            )

        return ranked

    async def _recency_search(
        self,
        request: RetrievalRequest,
    ) -> list[RankedMemory]:
        """Search by recency (most recent first)."""
        stmt = (
            select(MemoryModel)
            .where(MemoryModel.user_id == request.user_id)
            .where(
                (MemoryModel.valid_until.is_(None))
                | (MemoryModel.valid_until > datetime.now(UTC))
            )
            .where(MemoryModel.valid_from <= datetime.now(UTC))
            .order_by(MemoryModel.created_at.desc())
            .limit(request.limit * 2)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        now = datetime.now(UTC)
        ranked = []
        for i, model in enumerate(models):
            memory = self._model_to_memory(model)
            # Recency score: exponential decay over 7 days
            age_hours = (now - memory.created_at).total_seconds() / 3600
            recency_score = 1.0 / (1.0 + age_hours / 168)  # 168 hours = 7 days
            ranked.append(
                RankedMemory(
                    memory=memory,
                    rank=i + 1,
                    source="recency",
                    raw_score=recency_score,
                )
            )

        return ranked

    def _model_to_memory(self, model: MemoryModel) -> Memory:
        """Convert SQLAlchemy model to domain object."""
        return Memory(
            memory_id=model.memory_id,
            user_id=model.user_id,
            content=model.content,
            content_type=model.content_type,
            temporal_level=TemporalLevel(model.temporal_level),
            valid_from=model.valid_from,
            valid_until=model.valid_until,
            base_salience=model.base_salience,
            outcome_adjustment=model.outcome_adjustment,
            retrieval_count=model.retrieval_count,
            decision_count=model.decision_count,
            positive_outcomes=model.positive_outcomes,
            negative_outcomes=model.negative_outcomes,
            promoted_from_level=(
                TemporalLevel(model.promoted_from_level)
                if model.promoted_from_level
                else None
            ),
            promotion_timestamp=model.promotion_timestamp,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _row_to_memory(self, row) -> Memory:
        """Convert raw SQL row to domain object."""
        return Memory(
            memory_id=row.memory_id,
            user_id=row.user_id,
            content=row.content,
            content_type=row.content_type,
            temporal_level=TemporalLevel(row.temporal_level),
            valid_from=row.valid_from,
            valid_until=row.valid_until,
            base_salience=row.base_salience,
            outcome_adjustment=row.outcome_adjustment,
            retrieval_count=row.retrieval_count,
            decision_count=row.decision_count,
            positive_outcomes=row.positive_outcomes,
            negative_outcomes=row.negative_outcomes,
            promoted_from_level=(
                TemporalLevel(row.promoted_from_level)
                if row.promoted_from_level
                else None
            ),
            promotion_timestamp=row.promotion_timestamp,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
