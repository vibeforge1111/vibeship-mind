"""Tests for v3 bridge module."""
import pytest
import tempfile
from pathlib import Path

from mind.v3.bridge import (
    V3Bridge,
    V3Config,
    V3ContextResult,
    get_v3_bridge,
    v3_context_for_recall,
)


class TestV3Config:
    """Test V3Config settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = V3Config()

        assert config.enabled is True
        assert config.use_v3_context is True
        assert config.use_v3_session is True
        assert config.fallback_on_error is True

    def test_custom_config(self):
        """Should accept custom settings."""
        config = V3Config(
            enabled=False,
            use_v3_context=False,
        )

        assert config.enabled is False
        assert config.use_v3_context is False


class TestV3ContextResult:
    """Test V3ContextResult dataclass."""

    def test_create_result(self):
        """Should create context result."""
        result = V3ContextResult(
            success=True,
            context="## Context\n- Item 1",
            items_count=1,
            source="v3",
        )

        assert result.success is True
        assert "Context" in result.context
        assert result.items_count == 1
        assert result.source == "v3"

    def test_result_with_error(self):
        """Should track errors."""
        result = V3ContextResult(
            success=False,
            context="",
            items_count=0,
            source="v3",
            error="Hook failed",
        )

        assert result.success is False
        assert result.error == "Hook failed"


class TestV3Bridge:
    """Test V3Bridge."""

    @pytest.fixture
    def bridge(self):
        """Create bridge with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield V3Bridge(project_path=Path(tmpdir))

    def test_create_bridge(self, bridge):
        """Should create bridge."""
        assert bridge is not None
        assert bridge.config.enabled is True

    def test_bridge_disabled(self):
        """Should work when disabled."""
        config = V3Config(enabled=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = V3Bridge(project_path=Path(tmpdir), config=config)

            result = bridge.get_context_for_prompt("test query")

            assert result.success is True
            assert result.source == "disabled"

    def test_get_context_for_prompt(self, bridge):
        """Should get context for prompt."""
        result = bridge.get_context_for_prompt("How do I fix the auth bug?")

        assert result.success is True
        assert isinstance(result.context, str)

    def test_get_context_empty_prompt(self, bridge):
        """Should handle empty prompt."""
        result = bridge.get_context_for_prompt("")

        assert result.success is True
        assert result.items_count == 0


class TestV3BridgeSession:
    """Test session management."""

    @pytest.fixture
    def bridge(self):
        """Create bridge with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield V3Bridge(project_path=Path(tmpdir))

    def test_record_session_event(self, bridge):
        """Should record session events."""
        result = bridge.record_session_event("read file auth.py")

        assert result is True

    def test_finalize_session(self, bridge):
        """Should finalize session."""
        bridge.record_session_event("did something")
        bridge.record_session_event("did another thing")
        bridge.record_session_event("finished task")

        result = bridge.finalize_session()

        assert result is not None
        assert result.success is True


class TestV3BridgeMemory:
    """Test memory management."""

    @pytest.fixture
    def bridge(self):
        """Create bridge with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield V3Bridge(project_path=Path(tmpdir))

    def test_add_memory(self, bridge):
        """Should add memory."""
        result = bridge.add_memory(
            content="Decided to use SQLite",
            memory_type="decision",
        )

        assert result is True

    def test_memory_retrieval(self, bridge):
        """Should retrieve added memories."""
        bridge.add_memory(
            content="Using JWT for authentication",
            memory_type="decision",
        )

        result = bridge.get_context_for_prompt("auth tokens JWT")

        assert result.success is True


class TestV3BridgeStats:
    """Test stats collection."""

    @pytest.fixture
    def bridge(self):
        """Create bridge with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield V3Bridge(project_path=Path(tmpdir))

    def test_get_stats(self, bridge):
        """Should return stats."""
        stats = bridge.get_stats()

        assert "enabled" in stats
        assert "hooks_initialized" in stats
        assert stats["enabled"] is True

    def test_stats_after_activity(self, bridge):
        """Should track activity in stats."""
        bridge.add_memory("test memory", "decision")
        bridge.record_session_event("test event")

        stats = bridge.get_stats()

        assert stats["session_events"] == 1


class TestGetV3Bridge:
    """Test bridge factory function."""

    def test_get_bridge(self):
        """Should get bridge instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = get_v3_bridge(Path(tmpdir))

            assert bridge is not None
            assert bridge.project_path == Path(tmpdir)

    def test_singleton_same_path(self):
        """Should reuse bridge for same path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge1 = get_v3_bridge(Path(tmpdir))
            bridge2 = get_v3_bridge(Path(tmpdir))

            assert bridge1 is bridge2


class TestV3ContextForRecall:
    """Test recall integration function."""

    def test_returns_legacy_context(self):
        """Should return legacy context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy = "## Legacy Context\n- Item 1"

            result = v3_context_for_recall(Path(tmpdir), legacy)

            assert result == legacy

    def test_handles_errors_gracefully(self):
        """Should return legacy on error."""
        # Invalid path should not crash
        legacy = "## Legacy Context"

        result = v3_context_for_recall(Path("/nonexistent/path"), legacy)

        assert result == legacy


class TestV3BridgeAPI:
    """Test API integration in V3Bridge."""

    @pytest.fixture
    def bridge(self):
        """Create bridge with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield V3Bridge(project_path=Path(tmpdir))

    def test_api_client_initialized(self, bridge):
        """Bridge initializes API client from config."""
        assert hasattr(bridge, "_api_client")
        assert bridge._api_client is not None

    def test_event_store_initialized(self, bridge):
        """Bridge initializes event store."""
        assert hasattr(bridge, "_event_store")
        assert bridge._event_store is not None

    def test_get_stats_includes_api(self, bridge):
        """Stats include API status."""
        stats = bridge.get_stats()
        assert "api_enabled" in stats
        # Without API key set, should be False
        assert stats["api_enabled"] is False

    @pytest.mark.asyncio
    async def test_finalize_session_async_no_api(self, bridge):
        """Finalize without API returns None."""
        result = await bridge.finalize_session_async()
        assert result is None

    @pytest.mark.asyncio
    async def test_categorize_text_decision(self, bridge):
        """Categorize text with decision keywords."""
        category, confidence = await bridge.categorize_text("I decided to use Redis for caching")
        assert category == "decision"
        assert confidence >= 0.7

    @pytest.mark.asyncio
    async def test_categorize_text_learning(self, bridge):
        """Categorize text with learning keywords."""
        category, confidence = await bridge.categorize_text("TIL that Python has walrus operator")
        assert category == "learning"
        assert confidence >= 0.7

    @pytest.mark.asyncio
    async def test_categorize_text_problem(self, bridge):
        """Categorize text with problem keywords."""
        category, confidence = await bridge.categorize_text("There's a bug in the login flow")
        assert category == "problem"
        assert confidence >= 0.7

    @pytest.mark.asyncio
    async def test_categorize_text_progress(self, bridge):
        """Categorize text with progress keywords."""
        category, confidence = await bridge.categorize_text("Fixed the authentication issue")
        assert category == "progress"
        assert confidence >= 0.7

    @pytest.mark.asyncio
    async def test_categorize_text_ambiguous(self, bridge):
        """Ambiguous text gets exploration category."""
        category, confidence = await bridge.categorize_text("Looking at the code")
        assert category == "exploration"
        assert confidence < 0.6  # Low confidence for ambiguous


class TestV3BridgeWatcher:
    """Test TranscriptWatcher integration in V3Bridge."""

    @pytest.fixture
    def bridge(self):
        """Create bridge with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield V3Bridge(project_path=Path(tmpdir))

    def test_watcher_initialized(self, bridge):
        """Bridge initializes transcript watcher."""
        assert hasattr(bridge, "_transcript_watcher")
        assert bridge._transcript_watcher is not None

    def test_process_transcript_turn(self, bridge):
        """Can process transcript turns."""
        turn = {
            "role": "assistant",
            "content": "I decided to use Redis for caching because it's faster.",
        }
        events = bridge.process_transcript_turn(turn)
        assert isinstance(events, int)

    def test_get_watcher_stats(self, bridge):
        """Can get watcher stats."""
        stats = bridge.get_watcher_stats()
        assert "turns_processed" in stats
        assert "events_extracted" in stats
        assert "decisions_stored" in stats

    def test_stats_includes_watcher(self, bridge):
        """Bridge stats include watcher stats."""
        stats = bridge.get_stats()
        assert "watcher" in stats
