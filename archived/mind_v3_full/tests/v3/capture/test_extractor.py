"""Tests for transcript event extraction."""
import pytest
from mind.v3.capture.extractor import TranscriptExtractor
from mind.v3.capture.events import EventType


class TestTranscriptExtractor:
    """Test TranscriptExtractor class."""

    def test_extract_user_message(self):
        """Should extract user message events."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "user",
            "content": "Help me fix this bug"
        }

        events = extractor.extract_from_turn(turn)

        assert len(events) >= 1
        user_msgs = [e for e in events if e.type == EventType.USER_MESSAGE]
        assert len(user_msgs) == 1
        assert "fix this bug" in user_msgs[0].content

    def test_extract_user_message_structured(self):
        """Should extract user message from structured content."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello world"}
            ]
        }

        events = extractor.extract_from_turn(turn)
        user_msgs = [e for e in events if e.type == EventType.USER_MESSAGE]
        assert len(user_msgs) == 1
        assert "Hello world" in user_msgs[0].content

    def test_extract_tool_call(self):
        """Should extract tool call events."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "input": {"file_path": "/foo/bar.py"}
                }
            ]
        }

        events = extractor.extract_from_turn(turn)

        tool_calls = [e for e in events if e.type == EventType.TOOL_CALL]
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "Read"
        assert tool_calls[0].tool_input["file_path"] == "/foo/bar.py"

    def test_extract_multiple_tool_calls(self):
        """Should extract multiple tool calls from single turn."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/a.py"}},
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/b.py"}},
            ]
        }

        events = extractor.extract_from_turn(turn)

        tool_calls = [e for e in events if e.type == EventType.TOOL_CALL]
        assert len(tool_calls) == 2

    def test_extract_assistant_text(self):
        """Should extract assistant text message."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": "Let me help you with that."
        }

        events = extractor.extract_from_turn(turn)

        assistant_msgs = [e for e in events if e.type == EventType.ASSISTANT_MESSAGE]
        assert len(assistant_msgs) == 1
        assert "help you" in assistant_msgs[0].content

    def test_extract_decision_keywords(self):
        """Should detect decisions from keywords in assistant messages."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": "I decided to use SQLite because it's portable and doesn't require a server."
        }

        events = extractor.extract_from_turn(turn)

        decisions = [e for e in events if e.type == EventType.DECISION]
        assert len(decisions) >= 1
        assert "SQLite" in decisions[0].action

    def test_extract_decision_chose(self):
        """Should detect 'chose' keyword."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": "I chose to implement this with async/await for better performance."
        }

        events = extractor.extract_from_turn(turn)

        decisions = [e for e in events if e.type == EventType.DECISION]
        assert len(decisions) >= 1

    def test_extract_decision_going_with(self):
        """Should detect 'going with' keyword."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": "I'm going with PostgreSQL for this project."
        }

        events = extractor.extract_from_turn(turn)

        decisions = [e for e in events if e.type == EventType.DECISION]
        assert len(decisions) >= 1

    def test_extract_from_transcript(self):
        """Should extract all events from full transcript."""
        extractor = TranscriptExtractor()

        transcript = [
            {"role": "user", "content": "Fix the bug"},
            {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/main.py"}}
            ]},
            {"role": "assistant", "content": "I decided to refactor the function."},
        ]

        events = extractor.extract_from_transcript(transcript)

        assert len(events) >= 3
        types = [e.type for e in events]
        assert EventType.USER_MESSAGE in types
        assert EventType.TOOL_CALL in types
        assert EventType.DECISION in types

    def test_decision_with_reasoning(self):
        """Should extract reasoning from decision."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": "I decided to use Redis because it provides fast caching and supports pub/sub."
        }

        events = extractor.extract_from_turn(turn)

        decisions = [e for e in events if e.type == EventType.DECISION]
        assert len(decisions) >= 1
        # Should have some reasoning
        assert decisions[0].reasoning != "" or "because" in decisions[0].action.lower()

    def test_short_text_no_false_decision(self):
        """Should not detect decision from very short text."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": "Using it."  # Too short to be a real decision
        }

        events = extractor.extract_from_turn(turn)

        decisions = [e for e in events if e.type == EventType.DECISION]
        assert len(decisions) == 0
