"""Integration tests for RetrievalService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mind.core.memory.models import Memory, TemporalLevel
from mind.core.memory.retrieval import RetrievalRequest
from mind.infrastructure.postgres.repositories import MemoryRepository
from mind.services.retrieval import RetrievalService


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_embedder():
    """Create mock embedder for tests."""
    embedder = AsyncMock()
    embedder.embed = AsyncMock(return_value=[0.1] * 1536)
    return embedder


class TestRetrievalServiceIntegration:
    """Integration tests for multi-source retrieval."""

    async def test_retrieval_with_single_source(
        self,
        session: AsyncSession,
        user_id,
        mock_embedder,
    ):
        """Retrieval should work with just salience-based scoring."""
        repo = MemoryRepository(session)

        # Create memories with different salience
        for i in range(5):
            memory = Memory(
                memory_id=uuid4(),
                user_id=user_id,
                content=f"Memory about topic {i}",
                content_type="fact",
                temporal_level=TemporalLevel.SITUATIONAL,
                valid_from=datetime.now(UTC),
                base_salience=0.3 + (i * 0.15),
            )
            await repo.create(memory)

        service = RetrievalService(session=session, embedder=mock_embedder)

        request = RetrievalRequest(
            user_id=user_id,
            query="topic",
            limit=3,
        )

        result = await service.retrieve(request)

        assert result.is_ok
        assert len(result.value.memories) <= 3
        assert result.value.latency_ms > 0

    async def test_retrieval_with_vector_search(
        self,
        session: AsyncSession,
        user_id,
        mock_embedder,
    ):
        """Retrieval should combine vector search with other sources."""
        repo = MemoryRepository(session)

        # Create memories with embeddings
        for i in range(5):
            memory = Memory(
                memory_id=uuid4(),
                user_id=user_id,
                content=f"Topic alpha discussion point {i}",
                content_type="fact",
                temporal_level=TemporalLevel.SITUATIONAL,
                valid_from=datetime.now(UTC),
                base_salience=0.5,
            )
            # Slightly varied embeddings
            embedding = [0.1 + (i * 0.02)] * 1536
            await repo.create(memory, embedding=embedding)

        service = RetrievalService(session=session, embedder=mock_embedder)

        request = RetrievalRequest(
            user_id=user_id,
            query="alpha topic",
            limit=5,
        )

        result = await service.retrieve(request)

        assert result.is_ok
        # Should have results from multiple sources
        for sm in result.value.memories:
            assert sm.final_score > 0

    async def test_retrieval_temporal_level_filter(
        self,
        session: AsyncSession,
        user_id,
        mock_embedder,
    ):
        """Retrieval should respect temporal level filters."""
        repo = MemoryRepository(session)

        # Create memories at different levels
        levels = [TemporalLevel.IMMEDIATE, TemporalLevel.IDENTITY]
        for level in levels:
            memory = Memory(
                memory_id=uuid4(),
                user_id=user_id,
                content=f"Memory at {level.name}",
                content_type="fact",
                temporal_level=level,
                valid_from=datetime.now(UTC),
                base_salience=0.8,
            )
            await repo.create(memory)

        service = RetrievalService(session=session, embedder=mock_embedder)

        # Only request IDENTITY level
        request = RetrievalRequest(
            user_id=user_id,
            query="memory",
            temporal_levels=[TemporalLevel.IDENTITY],
            limit=10,
        )

        result = await service.retrieve(request)

        assert result.is_ok
        for sm in result.value.memories:
            assert sm.memory.temporal_level == TemporalLevel.IDENTITY

    async def test_retrieval_min_salience_filter(
        self,
        session: AsyncSession,
        user_id,
        mock_embedder,
    ):
        """Retrieval should filter by minimum salience."""
        repo = MemoryRepository(session)

        # Create memories with low and high salience
        low = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="Low importance memory",
            content_type="fact",
            temporal_level=TemporalLevel.SITUATIONAL,
            valid_from=datetime.now(UTC),
            base_salience=0.2,
        )
        await repo.create(low)

        high = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="High importance memory",
            content_type="fact",
            temporal_level=TemporalLevel.SITUATIONAL,
            valid_from=datetime.now(UTC),
            base_salience=0.9,
        )
        await repo.create(high)

        service = RetrievalService(session=session, embedder=mock_embedder)

        request = RetrievalRequest(
            user_id=user_id,
            query="memory",
            min_salience=0.5,
            limit=10,
        )

        result = await service.retrieve(request)

        assert result.is_ok
        memory_ids = [sm.memory.memory_id for sm in result.value.memories]
        assert low.memory_id not in memory_ids
        assert high.memory_id in memory_ids

    async def test_retrieval_excludes_expired(
        self,
        session: AsyncSession,
        user_id,
        mock_embedder,
    ):
        """Retrieval should exclude expired memories."""
        repo = MemoryRepository(session)

        # Active memory
        active = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="Active memory",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC) - timedelta(hours=1),
            valid_until=datetime.now(UTC) + timedelta(hours=1),
            base_salience=0.7,
        )
        await repo.create(active)

        # Expired memory
        expired = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="Expired memory",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC) - timedelta(days=2),
            valid_until=datetime.now(UTC) - timedelta(days=1),
            base_salience=0.9,
        )
        await repo.create(expired)

        service = RetrievalService(session=session, embedder=mock_embedder)

        request = RetrievalRequest(
            user_id=user_id,
            query="memory",
            limit=10,
            include_expired=False,
        )

        result = await service.retrieve(request)

        assert result.is_ok
        memory_ids = [sm.memory.memory_id for sm in result.value.memories]
        assert active.memory_id in memory_ids
        assert expired.memory_id not in memory_ids


class TestRetrievalServiceFusion:
    """Tests for RRF fusion in retrieval."""

    async def test_fusion_combines_sources(
        self,
        session: AsyncSession,
        user_id,
        mock_embedder,
    ):
        """RRF fusion should combine multiple source rankings."""
        repo = MemoryRepository(session)

        # Create memories with different characteristics
        # High vector similarity but low salience
        vector_preferred = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="Vector similarity match",
            content_type="fact",
            temporal_level=TemporalLevel.SITUATIONAL,
            valid_from=datetime.now(UTC),
            base_salience=0.3,
        )
        await repo.create(vector_preferred, embedding=[0.1] * 1536)

        # Low vector similarity but high salience
        salience_preferred = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="High salience content",
            content_type="fact",
            temporal_level=TemporalLevel.SITUATIONAL,
            valid_from=datetime.now(UTC),
            base_salience=0.95,
        )
        await repo.create(salience_preferred, embedding=[0.9] * 1536)

        service = RetrievalService(session=session, embedder=mock_embedder)

        request = RetrievalRequest(
            user_id=user_id,
            query="content",
            limit=10,
        )

        result = await service.retrieve(request)

        assert result.is_ok
        # Both should be in results due to fusion
        memory_ids = [sm.memory.memory_id for sm in result.value.memories]
        assert vector_preferred.memory_id in memory_ids
        assert salience_preferred.memory_id in memory_ids

    async def test_retrieval_returns_trace_id(
        self,
        session: AsyncSession,
        user_id,
        mock_embedder,
    ):
        """Retrieval should return a trace ID for outcome tracking."""
        repo = MemoryRepository(session)

        memory = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="Test memory",
            content_type="fact",
            temporal_level=TemporalLevel.SITUATIONAL,
            valid_from=datetime.now(UTC),
            base_salience=0.5,
        )
        await repo.create(memory)

        service = RetrievalService(session=session, embedder=mock_embedder)

        request = RetrievalRequest(
            user_id=user_id,
            query="test",
            limit=5,
        )

        result = await service.retrieve(request)

        assert result.is_ok
        assert result.value.retrieval_id is not None
