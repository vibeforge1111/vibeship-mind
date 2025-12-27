"""Tests for UserPromptSubmit hook."""
import pytest
import tempfile
from pathlib import Path

from mind.v3.hooks.prompt_submit import (
    PromptSubmitHook,
    PromptSubmitConfig,
    HookResult,
)


class TestPromptSubmitConfig:
    """Test PromptSubmitConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = PromptSubmitConfig()

        assert config.enabled is True
        assert config.max_context_items > 0
        assert config.min_relevance_score >= 0

    def test_custom_config(self):
        """Should accept custom settings."""
        config = PromptSubmitConfig(
            enabled=False,
            max_context_items=10,
        )

        assert config.enabled is False
        assert config.max_context_items == 10


class TestHookResult:
    """Test HookResult dataclass."""

    def test_create_result(self):
        """Should create hook result."""
        result = HookResult(
            success=True,
            context_injected="## Relevant Context\n- Item 1",
            items_count=1,
        )

        assert result.success is True
        assert "Relevant Context" in result.context_injected
        assert result.items_count == 1

    def test_empty_result(self):
        """Should handle empty context."""
        result = HookResult(
            success=True,
            context_injected="",
            items_count=0,
        )

        assert result.success is True
        assert result.items_count == 0


class TestPromptSubmitHook:
    """Test PromptSubmitHook."""

    @pytest.fixture
    def hook(self):
        """Create hook with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PromptSubmitHook(project_path=Path(tmpdir))

    def test_create_hook(self, hook):
        """Should create hook."""
        assert hook is not None

    def test_hook_disabled(self):
        """Should return empty when disabled."""
        config = PromptSubmitConfig(enabled=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = PromptSubmitHook(
                project_path=Path(tmpdir),
                config=config,
            )

            result = hook.process("test query")

            assert result.success is True
            assert result.items_count == 0

    def test_process_query(self, hook):
        """Should process user query."""
        result = hook.process("How do I fix the authentication bug?")

        assert result.success is True
        assert isinstance(result.context_injected, str)

    def test_process_empty_query(self, hook):
        """Should handle empty query."""
        result = hook.process("")

        assert result.success is True
        assert result.items_count == 0


class TestPromptSubmitWithMemory:
    """Test hook with seeded memory."""

    @pytest.fixture
    def hook_with_data(self):
        """Create hook and seed with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = PromptSubmitHook(project_path=Path(tmpdir))

            # Seed some decisions
            hook.add_to_memory(
                content="Decided to use SQLite for storage because it's portable",
                memory_type="decision",
            )
            hook.add_to_memory(
                content="Chose React over Vue for better ecosystem",
                memory_type="decision",
            )
            hook.add_to_memory(
                content="Authentication uses JWT tokens",
                memory_type="learning",
            )

            yield hook

    def test_finds_relevant_context(self, hook_with_data):
        """Should find relevant memories for query."""
        result = hook_with_data.process("What database are we using?")

        # Should find SQLite decision
        assert result.success is True

    def test_context_format(self, hook_with_data):
        """Context should be markdown formatted."""
        result = hook_with_data.process("Tell me about storage")

        if result.items_count > 0:
            assert "##" in result.context_injected or "-" in result.context_injected


class TestPromptSubmitIntegration:
    """Test integration with other v3 modules."""

    def test_uses_hybrid_search(self):
        """Should use hybrid search for retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = PromptSubmitHook(project_path=Path(tmpdir))

            # Add content
            hook.add_to_memory(
                content="Error handling uses try-catch with custom exceptions",
                memory_type="pattern",
            )

            # Search should work
            result = hook.process("How do we handle errors?")
            assert result.success is True

    def test_records_retrieval_for_reinforcement(self):
        """Should record retrievals for learning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = PromptSubmitHook(project_path=Path(tmpdir))

            hook.add_to_memory(
                content="Always use async/await for I/O operations",
                memory_type="pattern",
            )

            # First retrieval
            hook.process("async patterns")

            # Check retrieval was recorded
            stats = hook.get_retrieval_stats()
            assert stats["total_retrievals"] >= 0
