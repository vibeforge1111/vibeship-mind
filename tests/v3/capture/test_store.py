"""Tests for event store."""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from mind.v3.capture.events import Event, EventType, ToolCallEvent, DecisionEvent
from mind.v3.capture.store import EventStore


@pytest.fixture
def temp_store():
    """Create a temporary event store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(Path(tmpdir) / "events")
        yield store


class TestEventStore:
    """Test EventStore class."""

    def test_create_store(self, temp_store):
        """Should create store directory."""
        assert temp_store.path.exists()

    def test_append_event(self, temp_store):
        """Should append event to store."""
        event = ToolCallEvent(tool_name="Read", tool_input={"file_path": "/foo"})

        temp_store.append(event)

        events = list(temp_store.iter_events())
        assert len(events) == 1
        assert events[0]["tool_name"] == "Read"

    def test_append_multiple_events(self, temp_store):
        """Should append multiple events in order."""
        e1 = ToolCallEvent(tool_name="Read", tool_input={})
        e2 = ToolCallEvent(tool_name="Write", tool_input={})
        e3 = DecisionEvent(action="Used X", reasoning="Because Y")

        temp_store.append(e1)
        temp_store.append(e2)
        temp_store.append(e3)

        events = list(temp_store.iter_events())
        assert len(events) == 3
        assert events[0]["tool_name"] == "Read"
        assert events[1]["tool_name"] == "Write"
        assert events[2]["action"] == "Used X"

    def test_events_persisted_to_file(self, temp_store):
        """Events should be persisted to JSONL file."""
        event = ToolCallEvent(tool_name="Read", tool_input={})
        temp_store.append(event)

        # Create new store instance pointing to same directory
        store2 = EventStore(temp_store.path)
        events = list(store2.iter_events())

        assert len(events) == 1

    def test_iter_events_since(self, temp_store):
        """Should filter events by timestamp."""
        # Create event with explicit past timestamp
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        e1 = ToolCallEvent(tool_name="Read", tool_input={})
        e1.timestamp = past
        temp_store.append(e1)

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

        e2 = ToolCallEvent(tool_name="Write", tool_input={})
        temp_store.append(e2)

        events = list(temp_store.iter_events(since=cutoff))
        assert len(events) == 1
        assert events[0]["tool_name"] == "Write"

    def test_iter_events_by_type(self, temp_store):
        """Should filter events by type."""
        temp_store.append(ToolCallEvent(tool_name="Read", tool_input={}))
        temp_store.append(DecisionEvent(action="Used X"))
        temp_store.append(ToolCallEvent(tool_name="Write", tool_input={}))

        events = list(temp_store.iter_events(event_types=["decision"]))
        assert len(events) == 1
        assert events[0]["action"] == "Used X"

    def test_get_event_count(self, temp_store):
        """Should return correct event count."""
        assert temp_store.count() == 0

        temp_store.append(ToolCallEvent(tool_name="Read", tool_input={}))
        assert temp_store.count() == 1

        temp_store.append(ToolCallEvent(tool_name="Write", tool_input={}))
        assert temp_store.count() == 2

    def test_get_latest(self, temp_store):
        """Should return latest N events."""
        for i in range(5):
            temp_store.append(ToolCallEvent(tool_name=f"Tool{i}", tool_input={}))

        latest = temp_store.get_latest(3)
        assert len(latest) == 3
        # Most recent first
        assert latest[0]["tool_name"] == "Tool4"
        assert latest[1]["tool_name"] == "Tool3"
        assert latest[2]["tool_name"] == "Tool2"

    def test_daily_file_rotation(self, temp_store):
        """Should create separate files for different dates."""
        # This tests the internal file organization
        event = ToolCallEvent(tool_name="Read", tool_input={})
        temp_store.append(event)

        # Check that a dated file was created
        files = list(temp_store.path.glob("*.jsonl"))
        assert len(files) == 1
        assert files[0].name.endswith(".jsonl")
        # File should be named with date
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in files[0].name
