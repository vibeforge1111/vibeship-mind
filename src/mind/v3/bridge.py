"""
Bridge module for v3 integration with MCP server.

Provides a clean interface for the MCP server to use v3 modules
while maintaining backward compatibility with legacy code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .graph.store import GraphStore
from .hooks import PromptSubmitHook, PromptSubmitConfig, HookResult
from .hooks import SessionEndHook, SessionEndConfig, SessionEndResult
from .autonomy.tracker import AutonomyTracker


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

        # Initialize persistent storage
        self._graph_store: GraphStore | None = None

        # Initialize hooks
        self._prompt_hook: PromptSubmitHook | None = None
        self._session_hook: SessionEndHook | None = None
        self._seeded_count: int = 0

        # Initialize autonomy tracker
        self._autonomy: AutonomyTracker | None = None

        if self.config.enabled:
            self._init_storage()
            self._init_hooks()
            self._autonomy = AutonomyTracker()

    def _init_storage(self) -> None:
        """Initialize persistent storage."""
        try:
            store_path = self.project_path / ".mind" / "v3" / "graph"
            self._graph_store = GraphStore(store_path)
        except Exception:
            # Fall back to no persistence
            self._graph_store = None

    def _init_hooks(self) -> None:
        """Initialize v3 hooks."""
        try:
            self._prompt_hook = PromptSubmitHook(
                project_path=self.project_path,
                config=PromptSubmitConfig(),
                graph_store=self._graph_store,
            )
            self._session_hook = SessionEndHook(
                project_path=self.project_path,
                config=SessionEndConfig(),
                graph_store=self._graph_store,
            )
            # Seed from MEMORY.md (only adds new memories)
            self._seeded_count = self._seed_from_memory()
        except Exception:
            # Silently fail - v3 is optional
            self._prompt_hook = None
            self._session_hook = None

    def _seed_from_memory(self) -> int:
        """
        Seed v3 memory from existing MEMORY.md.

        Now runs incrementally - checks each entry before adding to avoid
        duplicates. Safe to call multiple times; new MEMORY.md entries
        will be synced to v3.

        Returns:
            Total number of memories in store after seeding
        """
        if not self._prompt_hook:
            return 0

        memory_file = self.project_path / ".mind" / "MEMORY.md"
        if not memory_file.exists():
            return self._graph_store.memory_count() if self._graph_store else 0

        def add_if_new(text: str, mem_type: str) -> bool:
            """Add memory only if it doesn't already exist."""
            text = text.strip()
            if not text:
                return False
            # Check for duplicates using GraphStore
            if self._graph_store and self._graph_store.memory_exists(text):
                return False
            self._prompt_hook.add_to_memory(text, mem_type)
            return True

        try:
            content = memory_file.read_text(encoding="utf-8")
            added = 0

            # Extract decisions
            for match in re.finditer(r"(?:decided|chose|going with|using)[:\s]+(.+?)(?:\n|$)", content, re.IGNORECASE):
                if add_if_new(match.group(0), "decision"):
                    added += 1

            # Extract learnings
            for match in re.finditer(r"(?:learned|discovered|realized|turns out|TIL|gotcha)[:\s]+(.+?)(?:\n|$)", content, re.IGNORECASE):
                if add_if_new(match.group(0), "learning"):
                    added += 1

            # Extract problems
            for match in re.finditer(r"(?:problem|issue|bug|stuck on|blocked)[:\s]+(.+?)(?:\n|$)", content, re.IGNORECASE):
                if add_if_new(match.group(0), "problem"):
                    added += 1

            # Extract from Key section (important decisions)
            key_match = re.search(r"## Key.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
            if key_match:
                for line in key_match.group(1).strip().split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        if add_if_new(line[2:], "decision"):
                            added += 1

            # Extract from Gotchas section
            gotcha_match = re.search(r"## Gotchas.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
            if gotcha_match:
                for line in gotcha_match.group(1).strip().split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        if add_if_new(line[2:], "learning"):
                            added += 1

            # Return total count (existing + newly added)
            return self._graph_store.memory_count() if self._graph_store else added
        except Exception:
            return self._graph_store.memory_count() if self._graph_store else 0

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
            "persistent": self._graph_store is not None,
            "seeded_from_memory": self._seeded_count,
        }

        if self._prompt_hook:
            stats["retrieval"] = self._prompt_hook.get_retrieval_stats()

        if self._session_hook:
            stats["session_events"] = self._session_hook.event_count

        if self._autonomy:
            stats["autonomy"] = self._autonomy.get_summary()

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
    session_query: str = "",
) -> str:
    """
    Append v3 context to legacy context for mind_recall.

    This is the integration point for the MCP server.
    Called from handle_recall() to optionally add v3 context.

    Args:
        project_path: Path to project
        legacy_context: Context from legacy ContextGenerator
        session_query: Optional query from session experiences

    Returns:
        Combined context (legacy + v3)
    """
    try:
        bridge = get_v3_bridge(project_path)
        if not bridge.config.enabled:
            return legacy_context

        # If we have a session query, use it to find relevant v3 context
        if session_query and bridge._prompt_hook:
            result = bridge.get_context_for_prompt(session_query)
            if result.success and result.items_count > 0:
                # Append v3 context after legacy context
                return legacy_context + "\n\n" + result.context

        return legacy_context

    except Exception:
        # On any error, return legacy context unchanged
        return legacy_context
