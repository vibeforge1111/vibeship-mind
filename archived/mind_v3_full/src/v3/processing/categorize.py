"""
Event categorizer for Mind v3.

Categorizes raw events into semantic types:
- decision: Choices made between alternatives
- learning: New knowledge gained
- problem: Issues encountered
- progress: Work completed
- exploration: Code reading/understanding
- routine: Standard operations (filtered out)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..capture.events import Event, UserMessageEvent, AssistantMessageEvent
from ..capture.events import ToolCallEvent, ErrorEvent, DecisionEvent

if TYPE_CHECKING:
    from ..api.client import ClaudeClient

logger = logging.getLogger(__name__)


@dataclass
class CategorizedEvent:
    """Event with category assignment."""
    event: Event
    category: str
    confidence: float


class EventCategorizer:
    """
    Categorizes raw events into types.

    Uses local heuristics first, escalates to Haiku
    when confidence is low and API is enabled.
    """

    CATEGORIES = [
        "decision",
        "learning",
        "problem",
        "progress",
        "exploration",
        "routine",
    ]

    # Keyword patterns for local categorization
    DECISION_PATTERNS = [
        r"\b(decided|chose|going with|using|went with|settled on)\b",
        r"\b(will use|let's use|picked|selected)\b",
        r"\binstead of\b",
    ]

    LEARNING_PATTERNS = [
        r"\b(learned|discovered|realized|turns out|TIL)\b",
        r"\b(gotcha|figured out|now I know)\b",
        r"\b(apparently|interestingly)\b",
    ]

    PROBLEM_PATTERNS = [
        r"\b(bug|error|issue|problem|fails?|broken)\b",
        r"\b(stuck|blocked|can't|cannot|doesn't work)\b",
        r"\b(exception|crash|timeout)\b",
    ]

    PROGRESS_PATTERNS = [
        r"\b(fixed|resolved|completed|done|shipped)\b",
        r"\b(implemented|added|created|built)\b",
        r"\b(works now|passing|success)\b",
    ]

    # Routine tool names that should be filtered out
    ROUTINE_TOOLS = {"Read", "Glob", "Grep", "Bash", "LSP"}

    def __init__(self):
        """Initialize categorizer."""
        self._decision_re = re.compile("|".join(self.DECISION_PATTERNS), re.IGNORECASE)
        self._learning_re = re.compile("|".join(self.LEARNING_PATTERNS), re.IGNORECASE)
        self._problem_re = re.compile("|".join(self.PROBLEM_PATTERNS), re.IGNORECASE)
        self._progress_re = re.compile("|".join(self.PROGRESS_PATTERNS), re.IGNORECASE)

    async def categorize(
        self,
        events: list[Event],
        client: "ClaudeClient | None" = None,
    ) -> list[CategorizedEvent]:
        """
        Categorize events.

        Args:
            events: Events to categorize
            client: Optional API client for escalation

        Returns:
            Non-routine events with categories
        """
        results = []

        for event in events:
            category, confidence = self._local_categorize(event)

            # Escalate to API if low confidence and client available
            if confidence < 0.6 and client and client.enabled:
                api_category = await self._api_categorize(event, client)
                if api_category:
                    category = api_category
                    confidence = 0.9

            # Filter out routine events
            if category != "routine":
                results.append(CategorizedEvent(
                    event=event,
                    category=category,
                    confidence=confidence,
                ))

        return results

    def _local_categorize(self, event: Event) -> tuple[str, float]:
        """
        Categorize event using local heuristics.

        Args:
            event: Event to categorize

        Returns:
            Tuple of (category, confidence)
        """
        # Tool calls are mostly routine
        if isinstance(event, ToolCallEvent):
            if event.tool_name in self.ROUTINE_TOOLS:
                return "routine", 0.9
            elif event.tool_name in ("Edit", "Write"):
                return "progress", 0.7
            return "exploration", 0.6

        # Errors are problems
        if isinstance(event, ErrorEvent):
            return "problem", 0.9

        # Decision events are obviously decisions
        if isinstance(event, DecisionEvent):
            return "decision", 0.95

        # For user/assistant messages, check content
        content = ""
        if isinstance(event, UserMessageEvent):
            content = event.content
        elif isinstance(event, AssistantMessageEvent):
            content = event.content

        if content:
            if self._decision_re.search(content):
                return "decision", 0.8
            if self._learning_re.search(content):
                return "learning", 0.8
            # Check progress before problem - "fixed bug" is progress, not problem
            if self._progress_re.search(content):
                return "progress", 0.7
            if self._problem_re.search(content):
                return "problem", 0.7

            # Default to exploration for messages with content
            return "exploration", 0.5

        return "routine", 0.5

    async def _api_categorize(
        self,
        event: Event,
        client: "ClaudeClient",
    ) -> str | None:
        """
        Categorize using API.

        Args:
            event: Event to categorize
            client: API client

        Returns:
            Category string or None
        """
        content = ""
        if isinstance(event, UserMessageEvent):
            content = event.content
        elif isinstance(event, AssistantMessageEvent):
            content = event.content
        elif isinstance(event, ErrorEvent):
            content = f"{event.error_type}: {event.error_message}"

        if not content:
            return None

        prompt = f"""Categorize this text into exactly one category:
- decision: A choice between alternatives
- learning: New knowledge or discovery
- problem: An issue or bug
- progress: Work completed
- exploration: Code reading or understanding

Text: {content[:500]}

Reply with just the category name."""

        try:
            response = await client.call_haiku(prompt)
            category = response.strip().lower()
            if category in self.CATEGORIES:
                return category
        except Exception:
            logger.debug("API categorization failed", exc_info=True)

        return None

    def _local_categorize_text(self, text: str) -> tuple[str, float]:
        """
        Categorize raw text using local heuristics.

        Args:
            text: Text to categorize

        Returns:
            Tuple of (category, confidence)
        """
        if not text:
            return "exploration", 0.5

        # Check progress before problem - "fixed bug" is progress, not problem
        if self._decision_re.search(text):
            return "decision", 0.8
        if self._learning_re.search(text):
            return "learning", 0.8
        if self._progress_re.search(text):
            return "progress", 0.7
        if self._problem_re.search(text):
            return "problem", 0.7

        return "exploration", 0.5

    async def _api_categorize_text(
        self,
        text: str,
        client: "ClaudeClient",
    ) -> str | None:
        """
        Categorize raw text using API.

        Args:
            text: Text to categorize
            client: API client

        Returns:
            Category string or None
        """
        if not text:
            return None

        prompt = f"""Categorize this text into exactly one category:
- decision: A choice between alternatives
- learning: New knowledge or discovery
- problem: An issue or bug
- progress: Work completed
- exploration: Code reading or understanding

Text: {text[:500]}

Reply with just the category name."""

        try:
            response = await client.call_haiku(prompt)
            category = response.strip().lower()
            if category in self.CATEGORIES:
                return category
        except Exception:
            logger.debug("API text categorization failed", exc_info=True)

        return None
