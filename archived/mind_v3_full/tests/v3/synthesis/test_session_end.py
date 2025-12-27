"""Tests for session end synthesizer."""
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from mind.v3.synthesis.session_end import SessionEndSynthesizer, SessionSummary
from mind.v3.capture.store import SessionEventStore
from mind.v3.capture.events import UserMessageEvent
from mind.v3.api.client import ClaudeClient, ClaudeConfig


class TestSessionSummary:
    """Test SessionSummary dataclass."""

    def test_create_summary(self):
        """Can create session summary."""
        summary = SessionSummary(
            session_id="20251226_120000",
            summary="Fixed auth bug and added tests",
            decisions=["chose JWT over sessions"],
            learnings=["Redis needs connection pooling"],
            unresolved=["need to add rate limiting"],
        )
        assert len(summary.decisions) == 1
        assert "auth" in summary.summary

    def test_summary_has_timestamp(self):
        """Summary has auto-generated timestamp."""
        summary = SessionSummary(
            session_id="20251226_120000",
            summary="test",
        )
        assert summary.timestamp is not None


class TestSessionEndSynthesizer:
    """Test SessionEndSynthesizer."""

    @pytest.fixture
    def event_store(self, tmp_path):
        """Create event store with test events."""
        store = SessionEventStore(tmp_path)
        store.add(UserMessageEvent(
            content="Fix the login bug",
        ))
        store.add(UserMessageEvent(
            content="decided to use bcrypt for hashing",
        ))
        return store

    @pytest.fixture
    def mock_graph_store(self):
        """Create mock graph store."""
        store = Mock()
        store.get_recent_memories.return_value = []
        store.get_recent_decisions.return_value = []
        store.get_recent_entities.return_value = []
        store.find_similar_decision.return_value = None
        store.add_decision.return_value = None
        store.add_session_summary.return_value = None
        store.update_decision.return_value = None
        return store

    @pytest.mark.asyncio
    async def test_synthesize_disabled_client(self, event_store, mock_graph_store):
        """Returns None when client is disabled."""
        client = ClaudeClient(ClaudeConfig())  # No API key
        synthesizer = SessionEndSynthesizer()
        result = await synthesizer.synthesize(event_store, mock_graph_store, client)
        assert result is None

    @pytest.mark.asyncio
    async def test_synthesize_with_mock_api(self, event_store, mock_graph_store):
        """Synthesizes with mocked API."""
        config = ClaudeConfig(api_key="sk-test", intelligence_level="BALANCED")
        client = ClaudeClient(config)

        # Mock the API call
        mock_response = """Summary: Fixed authentication bug using bcrypt.
Decisions:
- chose bcrypt for password hashing
Learnings:
- bcrypt is CPU-intensive
Unresolved:
- none
"""
        client.call_sonnet = AsyncMock(return_value=mock_response)

        synthesizer = SessionEndSynthesizer()
        result = await synthesizer.synthesize(event_store, mock_graph_store, client)

        assert result is not None
        assert "bcrypt" in result.summary or "authentication" in result.summary

    @pytest.mark.asyncio
    async def test_synthesize_ultra_uses_opus(self, event_store, mock_graph_store):
        """ULTRA level uses Opus for synthesis."""
        config = ClaudeConfig(api_key="sk-test", intelligence_level="ULTRA")
        client = ClaudeClient(config)

        mock_response = """Summary: Deep analysis completed.
Decisions:
- architectural choice
Learnings:
- important insight
"""
        client.call_opus = AsyncMock(return_value=mock_response)
        client.call_sonnet = AsyncMock(return_value="should not be called")

        synthesizer = SessionEndSynthesizer()
        result = await synthesizer.synthesize(event_store, mock_graph_store, client)

        assert result is not None
        client.call_opus.assert_called_once()
        client.call_sonnet.assert_not_called()

    def test_build_context(self, event_store, mock_graph_store):
        """Context includes events and recent data."""
        synthesizer = SessionEndSynthesizer()
        context = synthesizer._build_context(event_store, mock_graph_store)

        assert context is not None
        assert len(context.events) == 2

    def test_parse_response_extracts_sections(self):
        """Parse response extracts all sections."""
        synthesizer = SessionEndSynthesizer()
        response = """Summary: Did some work.
Decisions:
- chose option A
- chose option B
Learnings:
- learned thing 1
Unresolved:
- need to fix X
"""
        result = synthesizer._parse_response(response, "test_session")

        assert result.summary == "Did some work."
        assert len(result.decisions) == 2
        assert len(result.learnings) == 1
        assert len(result.unresolved) == 1

    def test_parse_response_handles_empty(self):
        """Parse handles empty response."""
        synthesizer = SessionEndSynthesizer()
        result = synthesizer._parse_response("", "test_session")

        assert result.summary == ""
        assert result.decisions == []
