"""NATS JetStream client management."""

import asyncio
from typing import Callable, Awaitable

import nats
from nats.aio.client import Client
from nats.js import JetStreamContext
from nats.js.api import StreamConfig, ConsumerConfig, DeliverPolicy, AckPolicy
import structlog

from mind.config import get_settings

logger = structlog.get_logger()


class NatsClient:
    """NATS JetStream client wrapper."""

    # Stream configuration for Mind events
    STREAM_NAME = "MIND_EVENTS"
    STREAM_SUBJECTS = ["mind.>"]  # All Mind events

    def __init__(self, url: str | None = None):
        settings = get_settings()
        self._url = url or settings.nats_url
        self._nc: Client | None = None
        self._js: JetStreamContext | None = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to NATS server and set up JetStream."""
        if self._connected:
            return

        log = logger.bind(url=self._url)
        log.info("nats_connecting")

        try:
            self._nc = await nats.connect(
                self._url,
                reconnect_time_wait=2,
                max_reconnect_attempts=5,
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback,
            )

            # Get JetStream context
            self._js = self._nc.jetstream()

            # Ensure stream exists
            await self._ensure_stream()

            self._connected = True
            log.info("nats_connected")

        except Exception as e:
            log.error("nats_connection_failed", error=str(e))
            raise

    async def _ensure_stream(self) -> None:
        """Ensure the Mind events stream exists."""
        try:
            await self._js.stream_info(self.STREAM_NAME)
            logger.info("nats_stream_exists", stream=self.STREAM_NAME)
        except nats.js.errors.NotFoundError:
            # Create stream
            config = StreamConfig(
                name=self.STREAM_NAME,
                subjects=self.STREAM_SUBJECTS,
                retention="limits",
                max_msgs=10_000_000,  # 10M messages
                max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                max_age=60 * 60 * 24 * 30,  # 30 days
                storage="file",
                num_replicas=1,  # Single node for dev, increase for prod
                duplicate_window=60 * 2,  # 2 min dedup window
            )
            await self._js.add_stream(config)
            logger.info("nats_stream_created", stream=self.STREAM_NAME)

    async def close(self) -> None:
        """Close NATS connection."""
        if self._nc and self._connected:
            await self._nc.close()
            self._connected = False
            logger.info("nats_disconnected")

    @property
    def jetstream(self) -> JetStreamContext:
        """Get JetStream context."""
        if not self._js:
            raise RuntimeError("NATS not connected. Call connect() first.")
        return self._js

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected and self._nc is not None and self._nc.is_connected

    async def _error_callback(self, e: Exception) -> None:
        """Handle NATS errors."""
        logger.error("nats_error", error=str(e))

    async def _disconnected_callback(self) -> None:
        """Handle disconnection."""
        logger.warning("nats_disconnected_unexpectedly")

    async def _reconnected_callback(self) -> None:
        """Handle reconnection."""
        logger.info("nats_reconnected")


# Global client instance
_nats_client: NatsClient | None = None


async def get_nats_client() -> NatsClient:
    """Get or create NATS client instance."""
    global _nats_client
    if _nats_client is None:
        _nats_client = NatsClient()
        await _nats_client.connect()
    return _nats_client


async def close_nats_client() -> None:
    """Close NATS client."""
    global _nats_client
    if _nats_client is not None:
        await _nats_client.close()
        _nats_client = None
