"""
Bridge module for v3 integration with MCP server.

Provides a clean interface for the MCP server to use v3 modules
while maintaining backward compatibility with legacy code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .hooks import PromptSubmitHook, PromptSubmitConfig, HookResult
from .hooks import SessionEndHook, SessionEndConfig, SessionEndResult


@dataclass
class V3Config:
    """Configuration for v3 integration."""

    enabled: bool = True
    use_v3_context: bool = True
    use_v3_session: bool = True
    fallback_on_error: bool = True  # Fall back to legacy on v3 error


@dataclass
class V3ContextResult:
    """Result from v3 context generation."""

    success: bool
    context: str
    items_count: int
    source: str = "v3"  # "v3" or "legacy"
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class V3Bridge:
    """
    Bridge between MCP server and v3 modules.

    Provides a stable interface that the MCP server can use,
    handling errors gracefully with fallback to legacy.
    """

    def __init__(
        self,
        project_path: Path,
        config: V3Config | None = None,
    ):
        """
        Initialize bridge.

        Args:
            project_path: Path to project directory
            config: Bridge configuration
        """
        self.project_path = project_path
        self.config = config or V3Config()

        # Initialize hooks
        self._prompt_hook: PromptSubmitHook | None = None
        self._session_hook: SessionEndHook | None = None

        if self.config.enabled:
            self._init_hooks()

    def _init_hooks(self) -> None:
        """Initialize v3 hooks."""
        try:
            self._prompt_hook = PromptSubmitHook(
                project_path=self.project_path,
                config=PromptSubmitConfig(),
            )
            self._session_hook = SessionEndHook(
                project_path=self.project_path,
                config=SessionEndConfig(),
            )
        except Exception:
            # Silently fail - v3 is optional
            self._prompt_hook = None
            self._session_hook = None

    def get_context_for_prompt(self, user_prompt: str) -> V3ContextResult:
        """
        Get relevant context for a user prompt.

        This is the main integration point for UserPromptSubmit hook.

        Args:
            user_prompt: The user's prompt text

        Returns:
            V3ContextResult with context to inject
        """
        if not self.config.enabled or not self.config.use_v3_context:
            return V3ContextResult(
                success=True,
                context="",
                items_count=0,
                source="disabled",
            )

        if not self._prompt_hook:
            return V3ContextResult(
                success=False,
                context="",
                items_count=0,
                source="v3",
                error="Hook not initialized",
            )

        try:
            result = self._prompt_hook.process(user_prompt)
            return V3ContextResult(
                success=result.success,
                context=result.context_injected,
                items_count=result.items_count,
                source="v3",
            )
        except Exception as e:
            return V3ContextResult(
                success=False,
                context="",
                items_count=0,
                source="v3",
                error=str(e),
            )

    def record_session_event(self, event: str) -> bool:
        """
        Record an event in the current session.

        Args:
            event: Event description

        Returns:
            True if recorded successfully
        """
        if not self.config.enabled or not self._session_hook:
            return False

        try:
            self._session_hook.add_event(event)
            return True
        except Exception:
            return False

    def finalize_session(self) -> SessionEndResult | None:
        """
        Finalize current session.

        Returns:
            Session end result or None if not available
        """
        if not self.config.enabled or not self._session_hook:
            return None

        try:
            return self._session_hook.finalize()
        except Exception:
            return None

    def add_memory(self, content: str, memory_type: str) -> bool:
        """
        Add content to v3 memory for retrieval.

        Args:
            content: Memory content
            memory_type: Type of memory

        Returns:
            True if added successfully
        """
        if not self.config.enabled or not self._prompt_hook:
            return False

        try:
            self._prompt_hook.add_to_memory(content, memory_type)
            return True
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get v3 system stats.

        Returns:
            Dictionary with stats
        """
        stats: dict[str, Any] = {
            "enabled": self.config.enabled,
            "hooks_initialized": self._prompt_hook is not None,
        }

        if self._prompt_hook:
            stats["retrieval"] = self._prompt_hook.get_retrieval_stats()

        if self._session_hook:
            stats["session_events"] = self._session_hook.event_count

        return stats


# Singleton for easy access from MCP server
_bridge_instance: V3Bridge | None = None


def get_v3_bridge(project_path: Path) -> V3Bridge:
    """
    Get or create v3 bridge for a project.

    Args:
        project_path: Path to project

    Returns:
        V3Bridge instance
    """
    global _bridge_instance

    # Create new instance if needed
    if _bridge_instance is None or _bridge_instance.project_path != project_path:
        _bridge_instance = V3Bridge(project_path)

    return _bridge_instance


def v3_context_for_recall(
    project_path: Path,
    legacy_context: str,
) -> str:
    """
    Append v3 context to legacy context for mind_recall.

    This is the integration point for the MCP server.
    Called from handle_recall() to optionally add v3 context.

    Args:
        project_path: Path to project
        legacy_context: Context from legacy ContextGenerator

    Returns:
        Combined context (legacy + v3)
    """
    try:
        bridge = get_v3_bridge(project_path)
        if not bridge.config.enabled:
            return legacy_context

        # For recall, we don't have a user prompt yet
        # Just return legacy context - v3 context comes via hooks
        return legacy_context

    except Exception:
        # On any error, return legacy context unchanged
        return legacy_context
