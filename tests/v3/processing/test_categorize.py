"""Tests for event categorizer."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from mind.v3.processing.categorize import EventCategorizer, CategorizedEvent
from mind.v3.capture.events import UserMessageEvent, ToolCallEvent, ErrorEvent


class TestEventCategorizer:
    """Test EventCategorizer."""

    def test_local_categorize_decision(self):
        """Detects decision keywords locally."""
        categorizer = EventCategorizer()
        event = UserMessageEvent(
            content="I decided to use PostgreSQL instead of MySQL",
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "decision"
        assert confidence >= 0.6

    def test_local_categorize_learning(self):
        """Detects learning keywords locally."""
        categorizer = EventCategorizer()
        event = UserMessageEvent(
            content="TIL that Python 3.11 is much faster",
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "learning"

    def test_local_categorize_problem(self):
        """Detects problem keywords locally."""
        categorizer = EventCategorizer()
        event = UserMessageEvent(
            content="Bug: the login fails with empty password",
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "problem"

    def test_local_categorize_progress(self):
        """Detects progress keywords locally."""
        categorizer = EventCategorizer()
        event = UserMessageEvent(
            content="Fixed the authentication bug, works now",
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "progress"

    def test_local_categorize_routine_tool(self):
        """Routine tool operations are filtered out."""
        categorizer = EventCategorizer()
        event = ToolCallEvent(
            tool_name="Read",
            tool_input={"file_path": "test.py"},
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "routine"

    def test_local_categorize_error_is_problem(self):
        """Error events are categorized as problems."""
        categorizer = EventCategorizer()
        event = ErrorEvent(
            error_type="SyntaxError",
            error_message="Unexpected token",
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "problem"
        assert confidence >= 0.8

    @pytest.mark.asyncio
    async def test_categorize_no_client(self):
        """Categorize works without API client."""
        categorizer = EventCategorizer()
        events = [
            UserMessageEvent(
                content="decided to use Redis",
            )
        ]
        results = await categorizer.categorize(events)
        assert len(results) == 1
        assert results[0].category == "decision"

    @pytest.mark.asyncio
    async def test_categorize_filters_routine(self):
        """Routine events are not returned."""
        categorizer = EventCategorizer()
        events = [
            ToolCallEvent(
                tool_name="Glob",
                tool_input={"pattern": "*.py"},
            )
        ]
        results = await categorizer.categorize(events)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_categorize_multiple_events(self):
        """Can categorize multiple events."""
        categorizer = EventCategorizer()
        events = [
            UserMessageEvent(content="decided to use JWT"),
            UserMessageEvent(content="learned about CORS"),
            UserMessageEvent(content="bug in the login flow"),
        ]
        results = await categorizer.categorize(events)
        assert len(results) == 3
        categories = [r.category for r in results]
        assert "decision" in categories
        assert "learning" in categories
        assert "problem" in categories

    def test_categorized_event_has_confidence(self):
        """CategorizedEvent includes confidence score."""
        event = UserMessageEvent(content="test")
        categorized = CategorizedEvent(
            event=event,
            category="decision",
            confidence=0.85,
        )
        assert categorized.confidence == 0.85
        assert categorized.category == "decision"
