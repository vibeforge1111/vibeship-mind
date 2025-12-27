"""Temporal client management."""

from temporalio.client import Client
import structlog

from mind.config import get_settings

logger = structlog.get_logger()


# Global client instance
_temporal_client: Client | None = None


async def get_temporal_client() -> Client:
    """Get or create Temporal client instance.

    Returns a connected Temporal client. The client is cached
    for reuse across requests.
    """
    global _temporal_client

    if _temporal_client is None:
        settings = get_settings()
        logger.info("temporal_connecting", host=settings.temporal_host)

        _temporal_client = await Client.connect(
            f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )

        logger.info("temporal_connected")

    return _temporal_client


async def close_temporal_client() -> None:
    """Close Temporal client connection."""
    global _temporal_client

    if _temporal_client is not None:
        # Note: Temporal client doesn't have an explicit close method
        # but we clear the reference for cleanup
        _temporal_client = None
        logger.info("temporal_disconnected")
