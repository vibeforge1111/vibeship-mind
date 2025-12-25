"""Tests for SessionEnd hook."""
import pytest
import tempfile
from pathlib import Path

from mind.v3.hooks.session_end import (
    SessionEndHook,
    SessionEndConfig,
    SessionEndResult,
)


class TestSessionEndConfig:
    """Test SessionEndConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = SessionEndConfig()

        assert config.enabled is True
        assert config.consolidate_memories is True
        assert config.min_session_length > 0

    def test_custom_config(self):
        """Should accept custom settings."""
        config = SessionEndConfig(
            enabled=False,
            consolidate_memories=False,
            min_session_length=10,
        )

        assert config.enabled is False
        assert config.consolidate_memories is False
        assert config.min_session_length == 10


class TestSessionEndResult:
    """Test SessionEndResult dataclass."""

    def test_create_result(self):
        """Should create session end result."""
        result = SessionEndResult(
            success=True,
            memories_consolidated=5,
            session_summary="Fixed auth bug, added tests",
        )

        assert result.success is True
        assert result.memories_consolidated == 5
        assert "auth" in result.session_summary

    def test_empty_result(self):
        """Should handle empty session."""
        result = SessionEndResult(
            success=True,
            memories_consolidated=0,
            session_summary="",
        )

        assert result.success is True
        assert result.memories_consolidated == 0


class TestSessionEndHook:
    """Test SessionEndHook."""

    @pytest.fixture
    def hook(self):
        """Create hook with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionEndHook(project_path=Path(tmpdir))

    def test_create_hook(self, hook):
        """Should create hook."""
        assert hook is not None

    def test_hook_disabled(self):
        """Should return empty when disabled."""
        config = SessionEndConfig(enabled=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = SessionEndHook(
                project_path=Path(tmpdir),
                config=config,
            )

            result = hook.finalize()

            assert result.success is True
            assert result.memories_consolidated == 0

    def test_finalize_empty_session(self, hook):
        """Should handle empty session."""
        result = hook.finalize()

        assert result.success is True
        assert result.memories_consolidated == 0

    def test_add_session_event(self, hook):
        """Should track session events."""
        hook.add_event("read file auth.py")
        hook.add_event("edited auth.py")

        assert hook.event_count == 2


class TestSessionEndWithActivity:
    """Test hook with session activity."""

    @pytest.fixture
    def active_hook(self):
        """Create hook and add activity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = SessionEndHook(project_path=Path(tmpdir))

            # Simulate session activity
            hook.add_event("read auth.py")
            hook.add_event("fixed token validation bug")
            hook.add_event("added unit tests")
            hook.add_event("ran tests - all pass")

            yield hook

    def test_consolidates_memories(self, active_hook):
        """Should consolidate session events."""
        result = active_hook.finalize()

        assert result.success is True

    def test_generates_summary(self, active_hook):
        """Should generate session summary."""
        result = active_hook.finalize()

        # Should have some summary
        assert isinstance(result.session_summary, str)

    def test_clears_session_after_finalize(self, active_hook):
        """Should clear session after finalize."""
        active_hook.finalize()

        assert active_hook.event_count == 0


class TestSessionEndIntegration:
    """Test integration with other v3 modules."""

    def test_uses_consolidation(self):
        """Should use memory consolidation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = SessionEndHook(project_path=Path(tmpdir))

            # Add many related events
            for i in range(10):
                hook.add_event(f"step {i}: working on auth")

            result = hook.finalize()
            assert result.success is True

    def test_respects_min_session_length(self):
        """Should skip consolidation for short sessions."""
        config = SessionEndConfig(min_session_length=5)
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = SessionEndHook(
                project_path=Path(tmpdir),
                config=config,
            )

            # Only 2 events, less than min
            hook.add_event("read file")
            hook.add_event("made edit")

            result = hook.finalize()
            assert result.success is True
            # Should still succeed but may not consolidate
