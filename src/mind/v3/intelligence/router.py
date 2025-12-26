"""
Intelligence router for Mind v3.

Routes requests to appropriate intelligence level based on configuration:
- LOCAL: Regex/rule-based only (free, instant)
- LOW: Basic NLP (spaCy, etc.)
- MEDIUM: AI batched (Haiku)
- HIGH: AI frequent (Sonnet)
- ULTRA: Real-time AI (Opus)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol


class IntelligenceLevel(str, Enum):
    """Intelligence levels, ordered by capability and cost."""

    LOCAL = "local"      # Regex/rule-based only (free)
    LOW = "low"          # Basic NLP (spaCy, etc.)
    MEDIUM = "medium"    # AI batched (Haiku)
    HIGH = "high"        # AI frequent (Sonnet)
    ULTRA = "ultra"      # Real-time AI (Opus)


# Level ordering for fallback
LEVEL_ORDER = [
    IntelligenceLevel.LOCAL,
    IntelligenceLevel.LOW,
    IntelligenceLevel.MEDIUM,
    IntelligenceLevel.HIGH,
    IntelligenceLevel.ULTRA,
]


class TaskHandler(Protocol):
    """Protocol for task handlers."""

    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
        """Execute the task."""
        ...


@dataclass
class TaskResult:
    """Result from a routed task."""

    content: dict[str, Any]
    confidence: float
    level_used: IntelligenceLevel
    handler_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RouterConfig:
    """Configuration for the intelligence router."""

    # Default levels for different task types
    decision_level: IntelligenceLevel = IntelligenceLevel.MEDIUM
    entity_level: IntelligenceLevel = IntelligenceLevel.LOCAL
    pattern_level: IntelligenceLevel = IntelligenceLevel.LOW
    synthesis_level: IntelligenceLevel = IntelligenceLevel.LOCAL

    # Whether to fallback to lower levels if higher not available
    enable_fallback: bool = True

    # Minimum confidence to accept result without fallback
    min_confidence: float = 0.5


class IntelligenceRouter:
    """
    Routes intelligence tasks to appropriate handlers based on level.

    Supports registration of handlers for different task types and levels,
    with automatic fallback to lower levels when higher aren't available.
    """

    def __init__(self, config: RouterConfig | None = None):
        """
        Initialize the router.

        Args:
            config: Router configuration. Uses defaults if not provided.
        """
        self.config = config or RouterConfig()

        # Handler registry: {task_type: {level: handler}}
        self._handlers: dict[str, dict[IntelligenceLevel, TaskHandler]] = {}

        # Level availability (some levels need API keys, etc.)
        self._available_levels: set[IntelligenceLevel] = {IntelligenceLevel.LOCAL}

    def register_handler(
        self,
        task_type: str,
        level: IntelligenceLevel,
        handler: TaskHandler,
        name: str | None = None,
    ) -> None:
        """
        Register a handler for a task type at a specific level.

        Args:
            task_type: Type of task (e.g., "decision", "entity", "pattern")
            level: Intelligence level this handler operates at
            handler: The handler function
            name: Optional name for the handler
        """
        if task_type not in self._handlers:
            self._handlers[task_type] = {}

        self._handlers[task_type][level] = handler

    def set_level_available(self, level: IntelligenceLevel, available: bool = True) -> None:
        """
        Mark a level as available or unavailable.

        Args:
            level: The level to update
            available: Whether it's available
        """
        if available:
            self._available_levels.add(level)
        else:
            self._available_levels.discard(level)

    def get_level_for_task(self, task_type: str) -> IntelligenceLevel:
        """
        Get the configured level for a task type.

        Args:
            task_type: Type of task

        Returns:
            Configured intelligence level
        """
        level_map = {
            "decision": self.config.decision_level,
            "entity": self.config.entity_level,
            "pattern": self.config.pattern_level,
            "synthesis": self.config.synthesis_level,
        }
        return level_map.get(task_type, IntelligenceLevel.LOCAL)

    def get_effective_level(self, task_type: str) -> IntelligenceLevel:
        """
        Get the effective level considering availability and fallback.

        Args:
            task_type: Type of task

        Returns:
            Effective level to use
        """
        desired_level = self.get_level_for_task(task_type)

        # If desired level is available, use it
        if desired_level in self._available_levels:
            return desired_level

        # If fallback is disabled, return desired (may fail)
        if not self.config.enable_fallback:
            return desired_level

        # Find highest available level at or below desired
        desired_idx = LEVEL_ORDER.index(desired_level)
        for idx in range(desired_idx, -1, -1):
            level = LEVEL_ORDER[idx]
            if level in self._available_levels:
                return level

        # Fallback to LOCAL if nothing else available
        return IntelligenceLevel.LOCAL

    def route(
        self,
        task_type: str,
        text: str,
        level: IntelligenceLevel | None = None,
        **kwargs: Any,
    ) -> TaskResult:
        """
        Route a task to the appropriate handler.

        Args:
            task_type: Type of task (e.g., "decision", "entity")
            text: Text to process
            level: Optional override for intelligence level
            **kwargs: Additional arguments for the handler

        Returns:
            TaskResult with content and metadata
        """
        # Determine effective level
        requested_level = level or self.get_effective_level(task_type)

        # Get handler (may return handler from a lower level if fallback)
        handler, actual_level = self._get_handler_with_level(task_type, requested_level)

        if handler is None:
            return TaskResult(
                content={},
                confidence=0.0,
                level_used=requested_level,
                handler_name="none",
                metadata={"error": f"No handler for {task_type} at {requested_level.value}"},
            )

        # Execute handler
        try:
            result = handler(text, **kwargs)

            # Wrap result
            return TaskResult(
                content=result.get("content", result),
                confidence=result.get("confidence", 0.5),
                level_used=actual_level,
                handler_name=result.get("handler_name", f"{task_type}_{actual_level.value}"),
                metadata=result.get("metadata", {}),
            )
        except Exception as e:
            return TaskResult(
                content={},
                confidence=0.0,
                level_used=actual_level,
                handler_name="error",
                metadata={"error": str(e)},
            )

    def _get_handler_with_level(
        self,
        task_type: str,
        level: IntelligenceLevel,
    ) -> tuple[TaskHandler | None, IntelligenceLevel]:
        """
        Get handler for task type at level, with fallback.

        Args:
            task_type: Type of task
            level: Desired level

        Returns:
            Tuple of (handler function or None, actual level used)
        """
        if task_type not in self._handlers:
            return None, level

        handlers = self._handlers[task_type]

        # Try exact level
        if level in handlers:
            return handlers[level], level

        # Try fallback to lower levels
        if self.config.enable_fallback:
            level_idx = LEVEL_ORDER.index(level)
            for idx in range(level_idx - 1, -1, -1):
                fallback_level = LEVEL_ORDER[idx]
                if fallback_level in handlers:
                    return handlers[fallback_level], fallback_level

        return None, level

    def get_available_handlers(self) -> dict[str, list[str]]:
        """
        Get summary of available handlers.

        Returns:
            Dict mapping task types to available levels
        """
        result = {}
        for task_type, handlers in self._handlers.items():
            result[task_type] = [level.value for level in handlers.keys()]
        return result


# Default router singleton
_default_router: IntelligenceRouter | None = None


def get_router(config: RouterConfig | None = None) -> IntelligenceRouter:
    """
    Get the default intelligence router.

    Args:
        config: Optional config to use if creating new router

    Returns:
        IntelligenceRouter instance
    """
    global _default_router

    if _default_router is None:
        _default_router = IntelligenceRouter(config)
        # Register default LOCAL handlers
        _register_local_handlers(_default_router)

    return _default_router


def reset_router() -> None:
    """Reset the default router."""
    global _default_router
    _default_router = None


def _register_local_handlers(router: IntelligenceRouter) -> None:
    """Register LOCAL level handlers with the router."""
    from .local import (
        extract_decisions_local,
        extract_entities_local,
        extract_patterns_local,
    )

    router.register_handler("decision", IntelligenceLevel.LOCAL, extract_decisions_local)
    router.register_handler("entity", IntelligenceLevel.LOCAL, extract_entities_local)
    router.register_handler("pattern", IntelligenceLevel.LOCAL, extract_patterns_local)
