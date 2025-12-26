"""Tests for event store."""
import pytest
import re
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from mind.v3.capture.events import Event, EventType, ToolCallEvent, DecisionEvent
from mind.v3.capture.store import EventStore, SessionEventStore


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


@pytest.fixture
def session_store():
    """Create a temporary session event store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionEventStore(Path(tmpdir))
        yield store


class TestSessionEventStore:
    """Test SessionEventStore class."""

    def test_add_event(self, session_store):
        """Should add events to the in-memory store."""
        event = ToolCallEvent(tool_name="Read", tool_input={"file_path": "/foo"})

        session_store.add(event)

        assert len(session_store.events) == 1
        assert session_store.events[0].tool_name == "Read"

    def test_session_id_format(self, session_store):
        """Session ID should have YYYYMMDD_HHMMSS format."""
        # Format: YYYYMMDD_HHMMSS
        pattern = r"^\d{8}_\d{6}$"
        assert re.match(pattern, session_store.session_id), (
            f"Session ID '{session_store.session_id}' doesn't match YYYYMMDD_HHMMSS format"
        )

    def test_get_events_since(self, session_store):
        """Should filter events by timestamp."""
        # Create event with past timestamp
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        e1 = ToolCallEvent(tool_name="Read", tool_input={})
        e1.timestamp = past
        session_store.add(e1)

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

        e2 = ToolCallEvent(tool_name="Write", tool_input={})
        session_store.add(e2)

        events = session_store.get_events_since(cutoff)
        assert len(events) == 1
        assert events[0].tool_name == "Write"

    def test_persist(self, session_store):
        """Should save session to .mind/v3/sessions/<session_id>.json."""
        event = ToolCallEvent(tool_name="Read", tool_input={})
        session_store.add(event)

        path = session_store.persist()

        # Check path structure
        assert path.exists()
        assert "sessions" in str(path)
        assert session_store.session_id in path.name
        assert path.suffix == ".json"

        # Verify content
        import json
        with open(path) as f:
            data = json.load(f)
        assert "session_id" in data
        assert "events" in data
        assert len(data["events"]) == 1

    def test_processing_callback(self, session_store):
        """Callback should be triggered every 10 events."""
        callback_count = [0]  # Use list to allow mutation in callback

        def callback(events):
            callback_count[0] += 1

        session_store.set_processing_callback(callback)

        # Add 25 events - should trigger callback twice (at 10 and 20)
        for i in range(25):
            event = ToolCallEvent(tool_name=f"Tool{i}", tool_input={})
            session_store.add(event)

        assert callback_count[0] == 2

    def test_clear(self, session_store):
        """Should clear all events."""
        session_store.add(ToolCallEvent(tool_name="Read", tool_input={}))
        session_store.add(ToolCallEvent(tool_name="Write", tool_input={}))
        assert len(session_store.events) == 2

        session_store.clear()

        assert len(session_store.events) == 0

    def test_add_event_sets_session_id(self, session_store):
        """Events should have session_id set when added."""
        event = ToolCallEvent(tool_name="Read", tool_input={})
        assert event.session_id is None

        session_store.add(event)

        assert session_store.events[0].session_id == session_store.session_id
