"""
Event types and schemas for Mind v3 event sourcing.

Events are immutable records of everything that happens during a session.
They form the foundation for the context graph.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class EventType(str, Enum):
    """Types of events captured from Claude Code sessions."""

    # Raw events from transcripts
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"

    # Extracted/inferred events
    DECISION = "decision"
    ERROR = "error"
    FILE_CHANGE = "file_change"
    PATTERN_DETECTED = "pattern_detected"


def generate_event_id() -> str:
    """Generate a unique event ID."""
    return f"evt_{uuid.uuid4().hex[:12]}"


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class Event(BaseModel):
    """Base event class for all Mind events."""

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=generate_event_id)
    timestamp: datetime = Field(default_factory=utc_now)
    type: EventType
    session_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type if isinstance(self.type, str) else self.type.value,
            "session_id": self.session_id,
            "data": self.data,
        }


class ToolCallEvent(Event):
    """Event representing a tool call by Claude."""

    type: EventType = EventType.TOOL_CALL
    tool_name: str
    tool_input: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["tool_name"] = self.tool_name
        d["tool_input"] = self.tool_input
        return d


class ToolResultEvent(Event):
    """Event representing a tool result."""

    type: EventType = EventType.TOOL_RESULT
    tool_name: str
    success: bool = True
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["tool_name"] = self.tool_name
        d["success"] = self.success
        d["result"] = self.result
        d["error"] = self.error
        return d


class UserMessageEvent(Event):
    """Event representing a user message."""

    type: EventType = EventType.USER_MESSAGE
    content: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["content"] = self.content
        return d


class AssistantMessageEvent(Event):
    """Event representing an assistant response."""

    type: EventType = EventType.ASSISTANT_MESSAGE
    content: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["content"] = self.content
        return d


class DecisionEvent(Event):
    """Event representing a decision made during the session."""

    type: EventType = EventType.DECISION
    action: str  # What was decided
    reasoning: str = ""  # Why (the gold)
    alternatives: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["action"] = self.action
        d["reasoning"] = self.reasoning
        d["alternatives"] = self.alternatives
        d["confidence"] = self.confidence
        return d


class ErrorEvent(Event):
    """Event representing an error encountered."""

    type: EventType = EventType.ERROR
    error_type: str = ""
    error_message: str = ""
    file_path: str | None = None
    line_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["error_type"] = self.error_type
        d["error_message"] = self.error_message
        d["file_path"] = self.file_path
        d["line_number"] = self.line_number
        return d


class FileChangeEvent(Event):
    """Event representing a file modification."""

    type: EventType = EventType.FILE_CHANGE
    file_path: str
    change_type: str  # created, modified, deleted
    lines_added: int = 0
    lines_removed: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["file_path"] = self.file_path
        d["change_type"] = self.change_type
        d["lines_added"] = self.lines_added
        d["lines_removed"] = self.lines_removed
        return d
