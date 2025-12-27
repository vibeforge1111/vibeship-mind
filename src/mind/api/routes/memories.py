"""Memory-related API endpoints."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from mind.core.memory.models import TemporalLevel
from mind.api.schemas.memory import (
    MemoryCreate,
    MemoryResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from mind.infrastructure.postgres.database import get_database
from mind.infrastructure.postgres.repositories import MemoryRepository
from mind.infrastructure.embeddings.openai import get_embedder
from mind.core.memory.models import Memory
from mind.core.memory.retrieval import RetrievalRequest
from mind.services.retrieval import RetrievalService
from mind.services.events import get_event_service
from mind.observability.metrics import metrics

logger = structlog.get_logger()
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

        created_memory = result.value

    # Publish event (fire-and-forget, don't block on failure)
    try:
        event_service = get_event_service()
        await event_service.publish_memory_created(created_memory)
    except Exception as e:
        logger.warning("event_publish_failed", error=str(e), memory_id=str(created_memory.memory_id))

    return MemoryResponse.from_domain(created_memory)


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
    fusion (vector, keyword, salience, recency) with RRF to find
    the most relevant memories for the given query.

    Sources combined:
    - Vector similarity (semantic search via embeddings)
    - Keyword/BM25 (full-text search)
    - Salience ranking (outcome-weighted importance)
    - Recency decay (time-based freshness)

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
        # Use retrieval service with RRF fusion
        embedder = get_embedder()
        service = RetrievalService(session=session, embedder=embedder)
        result = await service.retrieve(retrieval_request)

        if not result.is_ok:
            raise HTTPException(status_code=500, detail=result.error.to_dict())

        retrieval = result.value

        # Record metrics
        sources_used = set()
        for sm in retrieval.memories:
            if sm.vector_score:
                sources_used.add("vector")
            if sm.keyword_score:
                sources_used.add("keyword")
            if sm.salience_score:
                sources_used.add("salience")
            if sm.recency_score:
                sources_used.add("recency")

        metrics.observe_retrieval(
            latency_seconds=retrieval.latency_ms / 1000,
            sources_used=list(sources_used),
            result_count=len(retrieval.memories),
        )

        # Build response and event data while session is still active
        response = RetrieveResponse(
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

        # Capture event data for publishing after session closes
        event_data = {
            "retrieval_id": retrieval.retrieval_id,
            "query": request.query,
            "latency_ms": retrieval.latency_ms,
            "memories": [
                (sm.memory.memory_id, sm.rank, sm.final_score, "fusion")
                for sm in retrieval.memories
            ],
        }

    # Publish retrieval event (fire-and-forget, outside session)
    try:
        event_service = get_event_service()
        await event_service.publish_memory_retrieval(
            user_id=request.user_id,
            retrieval_id=event_data["retrieval_id"],
            query=event_data["query"],
            memories=event_data["memories"],
            latency_ms=event_data["latency_ms"],
        )
    except Exception as e:
        logger.warning("event_publish_failed", error=str(e), event_type="memory.retrieval")

    return response
