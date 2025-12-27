"""Memory-related API endpoints."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mind.core.memory.models import TemporalLevel
from mind.api.schemas.memory import (
    MemoryCreate,
    MemoryResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from mind.infrastructure.postgres.database import get_database
from mind.infrastructure.postgres.repositories import MemoryRepository
from mind.core.memory.models import Memory
from mind.core.memory.retrieval import RetrievalRequest

router = APIRouter()


@router.post("/", response_model=MemoryResponse, status_code=201)
async def create_memory(request: MemoryCreate) -> MemoryResponse:
    """Create a new memory.

    Memories are the core unit of context storage in Mind.
    They are stored in a hierarchical temporal structure.
    """
    memory = Memory(
        memory_id=uuid4(),
        user_id=request.user_id,
        content=request.content,
        content_type=request.content_type,
        temporal_level=request.temporal_level,
        valid_from=request.valid_from or datetime.now(UTC),
        valid_until=request.valid_until,
        base_salience=request.salience,
    )

    db = get_database()
    async with db.session() as session:
        repo = MemoryRepository(session)
        result = await repo.create(memory)

        if not result.is_ok:
            raise HTTPException(status_code=400, detail=result.error.to_dict())

        return MemoryResponse.from_domain(result.value)


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: UUID) -> MemoryResponse:
    """Get a memory by ID."""
    db = get_database()
    async with db.session() as session:
        repo = MemoryRepository(session)
        result = await repo.get(memory_id)

        if not result.is_ok:
            raise HTTPException(status_code=404, detail=result.error.to_dict())

        return MemoryResponse.from_domain(result.value)


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_memories(request: RetrieveRequest) -> RetrieveResponse:
    """Retrieve relevant memories for a query.

    This is the main retrieval endpoint. It uses multi-source
    fusion (vector, keyword, salience) to find the most relevant
    memories for the given query.

    Returns a trace_id that can be used to track the decision
    made with this context and observe outcomes.
    """
    retrieval_request = RetrievalRequest(
        user_id=request.user_id,
        query=request.query,
        limit=request.limit,
        temporal_levels=request.temporal_levels,
        min_salience=request.min_salience,
    )

    db = get_database()
    async with db.session() as session:
        repo = MemoryRepository(session)
        result = await repo.retrieve(retrieval_request)

        if not result.is_ok:
            raise HTTPException(status_code=500, detail=result.error.to_dict())

        retrieval = result.value
        return RetrieveResponse(
            retrieval_id=retrieval.retrieval_id,
            memories=[
                MemoryResponse.from_domain(sm.memory)
                for sm in retrieval.memories
            ],
            scores={
                str(sm.memory.memory_id): sm.final_score
                for sm in retrieval.memories
            },
            latency_ms=retrieval.latency_ms,
        )
