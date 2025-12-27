"""Event publishing to NATS JetStream."""

import orjson
import structlog
from nats.js.api import PubAck

from mind.core.events.base import Event, EventEnvelope
from mind.core.errors import ErrorCode, MindError, Result
from mind.infrastructure.nats.client import NatsClient

logger = structlog.get_logger()


class EventPublisher:
    """Publishes events to NATS JetStream."""

    def __init__(self, client: NatsClient):
        self._client = client

    async def publish(self, envelope: EventEnvelope) -> Result[PubAck]:
        """Publish an event envelope to NATS.

        Args:
            envelope: The event wrapped with metadata

        Returns:
            Result with PubAck on success, MindError on failure
        """
        subject = envelope.nats_subject()
        log = logger.bind(
            event_id=str(envelope.event_id),
            event_type=envelope.event_type.value,
            subject=subject,
            user_id=str(envelope.user_id),
        )

        try:
            # Serialize with orjson for speed
            data = orjson.dumps(envelope.model_dump(mode="json"))

            # Publish with message ID for deduplication
            ack = await self._client.jetstream.publish(
                subject=subject,
                payload=data,
                headers={
                    "Nats-Msg-Id": str(envelope.event_id),
                    "Content-Type": "application/json",
                },
            )

            log.info(
                "event_published",
                stream=ack.stream,
                sequence=ack.seq,
            )
            return Result.ok(ack)

        except Exception as e:
            log.error("event_publish_failed", error=str(e))
            return Result.err(
                MindError(
                    code=ErrorCode.EVENT_PUBLISH_FAILED,
                    message=f"Failed to publish event: {e}",
                    context={"event_id": str(envelope.event_id)},
                )
            )

    async def publish_event(
        self,
        event: Event,
        user_id,
        correlation_id=None,
        causation_id=None,
    ) -> Result[PubAck]:
        """Convenience method to wrap and publish a domain event.

        Args:
            event: The domain event to publish
            user_id: The user this event belongs to
            correlation_id: Optional correlation ID for tracing
            causation_id: Optional ID of the event that caused this one
        """
        envelope = EventEnvelope.wrap(
            event=event,
            user_id=user_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        return await self.publish(envelope)

    async def publish_batch(
        self,
        envelopes: list[EventEnvelope],
    ) -> list[Result[PubAck]]:
        """Publish multiple events.

        Note: This does not use transactions. Events are published
        individually but concurrently for performance.
        """
        import asyncio

        tasks = [self.publish(env) for env in envelopes]
        return await asyncio.gather(*tasks)
