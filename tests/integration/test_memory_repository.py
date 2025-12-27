"""Integration tests for MemoryRepository."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mind.core.errors import ErrorCode
from mind.core.memory.models import Memory, TemporalLevel
from mind.core.memory.retrieval import RetrievalRequest
from mind.core.decision.models import SalienceUpdate
from mind.infrastructure.postgres.repositories import MemoryRepository


pytestmark = pytest.mark.asyncio


class TestMemoryCreate:
    """Tests for memory creation."""

    async def test_create_memory_success(
        self,
        session: AsyncSession,
        user_id,
        sample_memory_data,
    ):
        """Creating a valid memory should succeed."""
        repo = MemoryRepository(session)

        memory = Memory(**sample_memory_data)
        result = await repo.create(memory)

        assert result.is_ok
        assert result.value.memory_id == memory.memory_id
        assert result.value.content == memory.content

    async def test_create_memory_with_embedding(
        self,
        session: AsyncSession,
        user_id,
        sample_memory_data,
    ):
        """Creating a memory with embedding should store the vector."""
        repo = MemoryRepository(session)

        memory = Memory(**sample_memory_data)
        embedding = [0.1] * 1536  # Mock embedding

        result = await repo.create(memory, embedding=embedding)

        assert result.is_ok
        assert result.value.memory_id == memory.memory_id

    async def test_create_multiple_memories(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Creating multiple memories should work."""
        repo = MemoryRepository(session)

        memories = []
        for i in range(5):
            memory = Memory(
                memory_id=uuid4(),
                user_id=user_id,
                content=f"Memory {i}",
                content_type="fact",
                temporal_level=TemporalLevel.IMMEDIATE,
                valid_from=datetime.now(UTC),
                base_salience=0.5 + (i * 0.1),
            )
            result = await repo.create(memory)
            assert result.is_ok
            memories.append(result.value)

        assert len(memories) == 5


class TestMemoryGet:
    """Tests for memory retrieval by ID."""

    async def test_get_existing_memory(
        self,
        session: AsyncSession,
        user_id,
        sample_memory_data,
    ):
        """Getting an existing memory should return it."""
        repo = MemoryRepository(session)

        memory = Memory(**sample_memory_data)
        await repo.create(memory)

        result = await repo.get(memory.memory_id)

        assert result.is_ok
        assert result.value.memory_id == memory.memory_id
        assert result.value.content == memory.content

    async def test_get_nonexistent_memory(
        self,
        session: AsyncSession,
    ):
        """Getting a nonexistent memory should return error."""
        repo = MemoryRepository(session)

        result = await repo.get(uuid4())

        assert not result.is_ok
        assert result.error.code == ErrorCode.MEMORY_NOT_FOUND


class TestMemoryRetrieve:
    """Tests for memory retrieval with filters."""

    async def test_retrieve_by_temporal_level(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Retrieval should filter by temporal level."""
        repo = MemoryRepository(session)

        # Create memories at different levels
        for level in TemporalLevel:
            memory = Memory(
                memory_id=uuid4(),
                user_id=user_id,
                content=f"Memory at {level.name}",
                content_type="fact",
                temporal_level=level,
                valid_from=datetime.now(UTC),
                base_salience=0.5,
            )
            await repo.create(memory)

        # Retrieve only IDENTITY level
        request = RetrievalRequest(
            user_id=user_id,
            query="test",
            temporal_levels=[TemporalLevel.IDENTITY],
            limit=10,
        )
        result = await repo.retrieve(request)

        assert result.is_ok
        for sm in result.value.memories:
            assert sm.memory.temporal_level == TemporalLevel.IDENTITY

    async def test_retrieve_by_salience(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Retrieval should filter by minimum salience."""
        repo = MemoryRepository(session)

        # Create memories with different salience
        saliences = [0.3, 0.5, 0.7, 0.9]
        for sal in saliences:
            memory = Memory(
                memory_id=uuid4(),
                user_id=user_id,
                content=f"Memory with salience {sal}",
                content_type="fact",
                temporal_level=TemporalLevel.SITUATIONAL,
                valid_from=datetime.now(UTC),
                base_salience=sal,
            )
            await repo.create(memory)

        # Retrieve only high salience
        request = RetrievalRequest(
            user_id=user_id,
            query="test",
            min_salience=0.6,
            limit=10,
        )
        result = await repo.retrieve(request)

        assert result.is_ok
        for sm in result.value.memories:
            assert sm.memory.effective_salience >= 0.6

    async def test_retrieve_excludes_expired(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Retrieval should exclude expired memories by default."""
        repo = MemoryRepository(session)

        # Create active memory
        active = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="Active memory",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC) - timedelta(hours=1),
            valid_until=datetime.now(UTC) + timedelta(hours=1),
            base_salience=0.8,
        )
        await repo.create(active)

        # Create expired memory
        expired = Memory(
            memory_id=uuid4(),
            user_id=user_id,
            content="Expired memory",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            valid_from=datetime.now(UTC) - timedelta(hours=2),
            valid_until=datetime.now(UTC) - timedelta(hours=1),
            base_salience=0.9,  # Higher salience but expired
        )
        await repo.create(expired)

        request = RetrievalRequest(
            user_id=user_id,
            query="test",
            limit=10,
            include_expired=False,
        )
        result = await repo.retrieve(request)

        assert result.is_ok
        memory_ids = [sm.memory.memory_id for sm in result.value.memories]
        assert active.memory_id in memory_ids
        assert expired.memory_id not in memory_ids

    async def test_retrieve_orders_by_salience(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Retrieval should order by effective salience."""
        repo = MemoryRepository(session)

        # Create memories with different salience
        for i in range(5):
            memory = Memory(
                memory_id=uuid4(),
                user_id=user_id,
                content=f"Memory {i}",
                content_type="fact",
                temporal_level=TemporalLevel.SITUATIONAL,
                valid_from=datetime.now(UTC),
                base_salience=0.1 + (i * 0.2),
            )
            await repo.create(memory)

        request = RetrievalRequest(
            user_id=user_id,
            query="test",
            limit=10,
        )
        result = await repo.retrieve(request)

        assert result.is_ok
        saliences = [sm.memory.effective_salience for sm in result.value.memories]
        assert saliences == sorted(saliences, reverse=True)


class TestVectorSearch:
    """Tests for vector similarity search."""

    async def test_vector_search_returns_results(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Vector search should return similar memories."""
        repo = MemoryRepository(session)

        # Create memories with embeddings
        for i in range(3):
            memory = Memory(
                memory_id=uuid4(),
                user_id=user_id,
                content=f"Memory {i}",
                content_type="fact",
                temporal_level=TemporalLevel.IMMEDIATE,
                valid_from=datetime.now(UTC),
                base_salience=0.5,
            )
            # Create slightly different embeddings
            embedding = [0.1 + (i * 0.01)] * 1536
            await repo.create(memory, embedding=embedding)

        # Search with similar embedding
        query_embedding = [0.1] * 1536
        results = await repo.vector_search(
            user_id=user_id,
            query_embedding=query_embedding,
            limit=5,
        )

        assert len(results) == 3
        # Results should be ordered by similarity
        similarities = [sim for _, sim in results]
        assert similarities == sorted(similarities, reverse=True)


class TestSalienceUpdate:
    """Tests for salience adjustment."""

    async def test_update_salience_positive(
        self,
        session: AsyncSession,
        user_id,
        sample_memory_data,
    ):
        """Positive outcome should increase salience."""
        repo = MemoryRepository(session)

        memory = Memory(**sample_memory_data)
        await repo.create(memory)

        trace_id = uuid4()
        adjustment = SalienceUpdate(
            memory_id=memory.memory_id,
            trace_id=trace_id,
            delta=0.05,
            reason="positive_outcome",
        )

        result = await repo.update_salience(memory.memory_id, adjustment)

        assert result.is_ok
        assert result.value.outcome_adjustment == 0.05
        assert result.value.positive_outcomes == 1

    async def test_update_salience_negative(
        self,
        session: AsyncSession,
        user_id,
        sample_memory_data,
    ):
        """Negative outcome should decrease salience."""
        repo = MemoryRepository(session)

        memory = Memory(**sample_memory_data)
        await repo.create(memory)

        trace_id = uuid4()
        adjustment = SalienceUpdate(
            memory_id=memory.memory_id,
            trace_id=trace_id,
            delta=-0.03,
            reason="negative_outcome",
        )

        result = await repo.update_salience(memory.memory_id, adjustment)

        assert result.is_ok
        assert result.value.outcome_adjustment == -0.03
        assert result.value.negative_outcomes == 1

    async def test_update_salience_nonexistent_memory(
        self,
        session: AsyncSession,
    ):
        """Updating salience for nonexistent memory should fail."""
        repo = MemoryRepository(session)

        adjustment = SalienceUpdate(
            memory_id=uuid4(),
            trace_id=uuid4(),
            delta=0.05,
            reason="positive_outcome",
        )

        result = await repo.update_salience(uuid4(), adjustment)

        assert not result.is_ok
        assert result.error.code == ErrorCode.MEMORY_NOT_FOUND
