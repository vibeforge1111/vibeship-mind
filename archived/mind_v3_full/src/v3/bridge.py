"""
Bridge module for v3 integration with MCP server.

Provides a clean interface for the MCP server to use v3 modules
while maintaining backward compatibility with legacy code.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .graph.store import GraphStore
from .hooks import PromptSubmitHook, PromptSubmitConfig, HookResult
from .hooks import SessionEndHook, SessionEndConfig, SessionEndResult
from .migration import MigrationManager, MigrationStats

# Autonomy tracker archived in v4 simplification
# from .autonomy.tracker import AutonomyTracker
from .api.client import ClaudeClient, ClaudeConfig
from .capture.store import SessionEventStore
from .synthesis.session_end import SessionEndSynthesizer, SessionSummary
from .processing.categorize import EventCategorizer
from .capture.watcher import TranscriptWatcher, WatcherConfig


@dataclass
class V3Config:
    """Configuration for v3 integration."""

    enabled: bool = True
    use_v3_context: bool = True
    use_v3_session: bool = True
    fallback_on_error: bool = True  # Fall back to legacy on v3 error
    auto_migrate: bool = True  # Auto-migrate from v2 on first init


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

        # Migration stats (populated on auto-migrate)
        self._migration_stats: MigrationStats | None = None

        # Autonomy tracker archived for v4 simplification
        self._autonomy = None

        # Initialize API client, event store, and categorizer
        self._api_client: ClaudeClient | None = None
        self._event_store: SessionEventStore | None = None
        self._categorizer: EventCategorizer | None = None
        self._transcript_watcher: TranscriptWatcher | None = None

        if self.config.enabled:
            self._init_storage()
            self._run_auto_migration()  # Migrate v2 data to v3 structured tables
            self._init_hooks()
            # Autonomy tracker archived for v4 simplification
            self._init_api()

    def _init_storage(self) -> None:
        """Initialize persistent storage."""
        try:
            store_path = self.project_path / ".mind" / "v3" / "graph"
            self._graph_store = GraphStore(store_path)
        except Exception:
            logger.debug("v3 storage init failed, falling back to no persistence", exc_info=True)
            self._graph_store = None

    def _run_auto_migration(self) -> None:
        """
        Automatically migrate/sync v2 data to v3 structured tables.

        This ensures users upgrading from v2 don't lose any experiences.
        - First run: Full migration
        - Subsequent runs: Incremental sync (faster)
        """
        if not self.config.auto_migrate or not self._graph_store:
            return

        try:
            manager = MigrationManager(self.project_path, self._graph_store)
            marker_file = self.project_path / ".mind" / "v3" / MigrationManager.MIGRATION_MARKER

            if not marker_file.exists():
                # First run - do full migration
                if manager.needs_migration():
                    self._migration_stats = manager.migrate()
            elif manager._has_new_content():
                # Subsequent runs - use faster incremental sync
                self._migration_stats = manager.sync_incremental()
        except Exception:
            logger.debug("v3 auto-migration failed, continuing without migration", exc_info=True)

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
            logger.debug("v3 hooks init failed, v3 features disabled", exc_info=True)
            self._prompt_hook = None
            self._session_hook = None

    def _init_api(self) -> None:
        """Initialize API client, event store, categorizer, and watcher."""
        try:
            self._api_client = ClaudeClient(ClaudeConfig.from_env())
            self._event_store = SessionEventStore(self.project_path)
            self._categorizer = EventCategorizer()
            # Initialize transcript watcher with graph store for persistence
            self._transcript_watcher = TranscriptWatcher(
                graph_store=self._graph_store,
                config=WatcherConfig(),
            )
        except Exception:
            logger.debug("v3 API init failed, API features disabled", exc_info=True)
            self._api_client = None
            self._event_store = None
            self._categorizer = EventCategorizer()  # Still useful for local categorization
            self._transcript_watcher = TranscriptWatcher(
                graph_store=self._graph_store,
                config=WatcherConfig(),
            )

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
            logger.debug("v3 seeding from MEMORY.md failed", exc_info=True)
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
            logger.debug("v3 record_session_event failed", exc_info=True)
            return False

    def process_transcript_turn(self, turn: dict) -> int:
        """
        Process a transcript turn for extraction.

        Automatically extracts decisions and entities from the turn
        and stores them in the graph.

        Args:
            turn: Conversation turn with 'role' and 'content'

        Returns:
            Number of events extracted
        """
        if not self.config.enabled or not self._transcript_watcher:
            return 0

        try:
            events = self._transcript_watcher.process_turn(turn)
            return len(events)
        except Exception:
            logger.debug("v3 process_transcript_turn failed", exc_info=True)
            return 0

    def get_watcher_stats(self) -> dict:
        """
        Get transcript watcher statistics.

        Returns:
            Dictionary with watcher stats
        """
        if not self._transcript_watcher:
            return {}

        return self._transcript_watcher.get_stats()

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
            logger.debug("v3 finalize_session failed", exc_info=True)
            return None

    async def finalize_session_async(self) -> SessionSummary | None:
        """
        Finalize session with AI synthesis.

        Uses SessionEndSynthesizer to generate an AI-powered summary
        of the session including decisions, learnings, and unresolved items.

        Returns:
            SessionSummary or None if API disabled or synthesis fails
        """
        if not self.config.enabled:
            return None

        if not self._api_client or not self._api_client.enabled:
            return None

        if not self._event_store or not self._graph_store:
            return None

        try:
            synthesizer = SessionEndSynthesizer()
            return await synthesizer.synthesize(
                self._event_store,
                self._graph_store,
                self._api_client,
            )
        except Exception:
            logger.debug("v3 finalize_session_async failed", exc_info=True)
            return None

    async def categorize_text(self, text: str) -> tuple[str, float]:
        """
        Categorize text message with optional API escalation.

        Uses local heuristics first, escalates to API when confidence is low
        and API is enabled.

        Args:
            text: Text message to categorize

        Returns:
            Tuple of (category, confidence)
            Categories: decision, learning, problem, progress, exploration
        """
        if not self._categorizer:
            return "exploration", 0.5

        # Use local categorization first
        category, confidence = self._categorizer._local_categorize_text(text)

        # Escalate to API if low confidence and API available
        if confidence < 0.6 and self._api_client and self._api_client.enabled:
            api_category = await self._categorizer._api_categorize_text(text, self._api_client)
            if api_category:
                return api_category, 0.9

        return category, confidence

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
            logger.debug("v3 add_memory failed", exc_info=True)
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
            "api_enabled": self._api_client.enabled if self._api_client else False,
        }

        # Include migration stats if available
        if self._migration_stats:
            stats["migration"] = {
                "memories_processed": self._migration_stats.memories_processed,
                "decisions_added": self._migration_stats.decisions_added,
                "entities_added": self._migration_stats.entities_added,
                "patterns_added": self._migration_stats.patterns_added,
                "errors": len(self._migration_stats.errors),
            }

        if self._prompt_hook:
            stats["retrieval"] = self._prompt_hook.get_retrieval_stats()

        if self._session_hook:
            stats["session_events"] = self._session_hook.event_count

        # Autonomy tracker archived for v4 simplification
        # if self._autonomy:
        #     stats["autonomy"] = self._autonomy.get_summary()

        if self._transcript_watcher:
            stats["watcher"] = self._transcript_watcher.get_stats()

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
        logger.debug("v3_context_for_recall failed, returning legacy context", exc_info=True)
        return legacy_context
