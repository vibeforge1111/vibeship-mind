"""Tests for event schema and validation."""
import pytest
from datetime import datetime
from mind.v3.capture.events import (
    Event,
    EventType,
    ToolCallEvent,
    ToolResultEvent,
    UserMessageEvent,
    AssistantMessageEvent,
    DecisionEvent,
    ErrorEvent,
    FileChangeEvent,
)


class TestEventType:
    """Test EventType enum."""

    def test_event_types_exist(self):
        """All required event types should exist."""
        assert EventType.TOOL_CALL
        assert EventType.TOOL_RESULT
        assert EventType.USER_MESSAGE
        assert EventType.ASSISTANT_MESSAGE
        assert EventType.DECISION
        assert EventType.ERROR
        assert EventType.FILE_CHANGE


class TestEvent:
    """Test base Event class."""

    def test_create_event(self):
        """Should create event with auto-generated id and timestamp."""
        event = Event(type=EventType.USER_MESSAGE, data={"content": "hello"})

        assert event.id is not None
        assert event.id.startswith("evt_")
        assert event.timestamp is not None
        assert event.type == EventType.USER_MESSAGE
        assert event.data == {"content": "hello"}

    def test_event_to_dict(self):
        """Should serialize to dictionary."""
        event = Event(type=EventType.USER_MESSAGE, data={"content": "hello"})
        d = event.to_dict()

        assert "id" in d
        assert "timestamp" in d
        assert d["type"] == "user_message"
        assert d["data"] == {"content": "hello"}

    def test_event_session_id(self):
        """Should support optional session_id."""
        event = Event(
            type=EventType.USER_MESSAGE,
            session_id="sess_abc123",
            data={}
        )
        assert event.session_id == "sess_abc123"


class TestToolCallEvent:
    """Test ToolCallEvent schema."""

    def test_create_tool_call_event(self):
        """Should create tool call event with required fields."""
        event = ToolCallEvent(
            tool_name="Read",
            tool_input={"file_path": "/foo/bar.py"},
        )

        assert event.type == EventType.TOOL_CALL
        assert event.tool_name == "Read"
        assert event.tool_input == {"file_path": "/foo/bar.py"}

    def test_tool_call_to_dict(self):
        """Should include tool fields in dict."""
        event = ToolCallEvent(
            tool_name="Write",
            tool_input={"content": "hello"},
        )
        d = event.to_dict()

        assert d["tool_name"] == "Write"
        assert d["tool_input"] == {"content": "hello"}


class TestToolResultEvent:
    """Test ToolResultEvent schema."""

    def test_create_success_result(self):
        """Should create successful tool result."""
        event = ToolResultEvent(
            tool_name="Read",
            success=True,
            result="file contents here",
        )

        assert event.type == EventType.TOOL_RESULT
        assert event.success is True
        assert event.result == "file contents here"
        assert event.error is None

    def test_create_error_result(self):
        """Should create error tool result."""
        event = ToolResultEvent(
            tool_name="Read",
            success=False,
            error="File not found",
        )

        assert event.success is False
        assert event.error == "File not found"


class TestDecisionEvent:
    """Test DecisionEvent schema."""

    def test_create_decision_event(self):
        """Should create decision event with reasoning."""
        event = DecisionEvent(
            action="Used SQLite for storage",
            reasoning="Need portability, single file",
            alternatives=["PostgreSQL", "JSON files"],
        )

        assert event.type == EventType.DECISION
        assert event.action == "Used SQLite for storage"
        assert event.reasoning == "Need portability, single file"
        assert "PostgreSQL" in event.alternatives
        assert "JSON files" in event.alternatives

    def test_decision_confidence(self):
        """Should support confidence score."""
        event = DecisionEvent(
            action="Chose functional style",
            confidence=0.85,
        )

        assert event.confidence == 0.85

    def test_decision_to_dict(self):
        """Should include decision fields in dict."""
        event = DecisionEvent(
            action="Used X",
            reasoning="Because Y",
            alternatives=["A", "B"],
            confidence=0.9,
        )
        d = event.to_dict()

        assert d["action"] == "Used X"
        assert d["reasoning"] == "Because Y"
        assert d["alternatives"] == ["A", "B"]
        assert d["confidence"] == 0.9


class TestErrorEvent:
    """Test ErrorEvent schema."""

    def test_create_error_event(self):
        """Should create error event with details."""
        event = ErrorEvent(
            error_type="TypeError",
            error_message="Cannot read property 'x' of undefined",
            file_path="/src/main.py",
            line_number=42,
        )

        assert event.type == EventType.ERROR
        assert event.error_type == "TypeError"
        assert event.error_message == "Cannot read property 'x' of undefined"
        assert event.file_path == "/src/main.py"
        assert event.line_number == 42


class TestFileChangeEvent:
    """Test FileChangeEvent schema."""

    def test_create_file_change_event(self):
        """Should create file change event."""
        event = FileChangeEvent(
            file_path="/src/main.py",
            change_type="modified",
            lines_added=10,
            lines_removed=5,
        )

        assert event.type == EventType.FILE_CHANGE
        assert event.file_path == "/src/main.py"
        assert event.change_type == "modified"
        assert event.lines_added == 10
        assert event.lines_removed == 5
