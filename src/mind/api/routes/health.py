"""Health check endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    database: str
    nats: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Basic health check - always returns OK if API is running."""
    return HealthResponse(status="healthy", version="5.0.0")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    """Readiness check - verifies all dependencies are connected."""
    from mind.infrastructure.postgres.database import get_database
    from mind.infrastructure.nats.client import _nats_client

    # Check database
    db_status = "disconnected"
    try:
        db = get_database()
        async with db.session() as session:
            await session.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        pass

    # Check NATS
    nats_status = "disconnected"
    if _nats_client and _nats_client.is_connected:
        nats_status = "connected"

    ready = db_status == "connected"  # NATS is optional

    return ReadinessResponse(
        ready=ready,
        database=db_status,
        nats=nats_status,
    )
