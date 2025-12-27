"""Tests for event models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mind.core.events.base import EventEnvelope, EventType
from mind.core.events.memory import MemoryCreated
from mind.core.memory.models import TemporalLevel


class TestEventType:
    """Tests for EventType enum."""

    def test_memory_events_exist(self):
        """Memory-related events should exist."""
        assert EventType.MEMORY_CREATED is not None
        assert EventType.MEMORY_PROMOTED is not None
        assert EventType.MEMORY_RETRIEVAL is not None
        assert EventType.MEMORY_SALIENCE_ADJUSTED is not None

    def test_decision_events_exist(self):
        """Decision-related events should exist."""
        assert EventType.DECISION_TRACKED is not None
        assert EventType.OUTCOME_OBSERVED is not None

    def test_event_type_values_are_dotted(self):
        """Event types should use dotted notation."""
        for event_type in EventType:
            assert "." in event_type.value


class TestMemoryCreated:
    """Tests for MemoryCreated event."""

    @pytest.fixture
    def sample_event(self) -> MemoryCreated:
        """Create a sample MemoryCreated event."""
        return MemoryCreated(
            memory_id=uuid4(),
            content="User prefers dark mode",
            content_type="preference",
            temporal_level=TemporalLevel.IDENTITY,
            base_salience=0.8,
            valid_from=datetime.now(UTC),
        )

    def test_event_type(self, sample_event: MemoryCreated):
        """Event type should be MEMORY_CREATED."""
        assert sample_event.event_type == EventType.MEMORY_CREATED

    def test_aggregate_id(self, sample_event: MemoryCreated):
        """Aggregate ID should be the memory ID."""
        assert sample_event.aggregate_id == sample_event.memory_id


class TestEventEnvelope:
    """Tests for EventEnvelope."""

    @pytest.fixture
    def sample_envelope(self) -> EventEnvelope:
        """Create a sample event envelope."""
        event = MemoryCreated(
            memory_id=uuid4(),
            content="Test memory",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            base_salience=1.0,
            valid_from=datetime.now(UTC),
        )
        return EventEnvelope.wrap(
            event=event,
            user_id=uuid4(),
        )

    def test_wrap_creates_envelope(self, sample_envelope: EventEnvelope):
        """Wrapping should create valid envelope."""
        assert sample_envelope.event_id is not None
        assert sample_envelope.event_type == EventType.MEMORY_CREATED
        assert sample_envelope.correlation_id is not None

    def test_nats_subject_format(self, sample_envelope: EventEnvelope):
        """NATS subject should follow pattern."""
        subject = sample_envelope.nats_subject()
        assert subject.startswith("mind.")
        assert str(sample_envelope.user_id) in subject

    def test_nats_subject_for_memory_created(self, sample_envelope: EventEnvelope):
        """Memory created event should have correct subject."""
        subject = sample_envelope.nats_subject()
        assert "memory.created" in subject

    def test_causation_chain(self):
        """Events should support causation chaining."""
        event1 = MemoryCreated(
            memory_id=uuid4(),
            content="First",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            base_salience=1.0,
            valid_from=datetime.now(UTC),
        )
        user_id = uuid4()
        envelope1 = EventEnvelope.wrap(event=event1, user_id=user_id)

        event2 = MemoryCreated(
            memory_id=uuid4(),
            content="Second (caused by first)",
            content_type="fact",
            temporal_level=TemporalLevel.IMMEDIATE,
            base_salience=1.0,
            valid_from=datetime.now(UTC),
        )
        envelope2 = EventEnvelope.wrap(
            event=event2,
            user_id=user_id,
            correlation_id=envelope1.correlation_id,  # Same trace
            causation_id=envelope1.event_id,  # Caused by first
        )

        assert envelope2.correlation_id == envelope1.correlation_id
        assert envelope2.causation_id == envelope1.event_id
