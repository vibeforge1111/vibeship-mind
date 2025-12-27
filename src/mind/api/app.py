"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from mind.config import get_settings
from mind.api.routes import health, memories, decisions
from mind.infrastructure.postgres.database import init_database, close_database
from mind.infrastructure.nats.client import get_nats_client, close_nats_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("app_starting")

    # Initialize connections
    try:
        await init_database()
        logger.info("database_connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        # Continue without database for health checks

    try:
        await get_nats_client()
        logger.info("nats_connected")
    except Exception as e:
        logger.warning("nats_connection_failed", error=str(e))
        # Continue without NATS - it's optional for basic API

    yield

    # Cleanup
    logger.info("app_stopping")
    await close_database()
    await close_nats_client()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Mind v5 API",
        description="Decision intelligence system for AI agents",
        version="5.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health.router, tags=["health"])
    app.include_router(memories.router, prefix="/v1/memories", tags=["memories"])
    app.include_router(decisions.router, prefix="/v1/decisions", tags=["decisions"])

    return app


# Application instance for uvicorn
app = create_app()
