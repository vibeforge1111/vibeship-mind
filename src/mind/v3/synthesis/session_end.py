"""
Session end synthesizer for Mind v3.

Uses AI to analyze session events and extract:
- Session summary
- Key decisions
- Important learnings
- Unresolved items
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..capture.events import Event, UserMessageEvent, AssistantMessageEvent

if TYPE_CHECKING:
    from ..api.client import ClaudeClient
    from ..capture.store import SessionEventStore

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Context for AI synthesis."""
    events: list[Event]
    memories_added: list[dict] = field(default_factory=list)
    decisions_made: list[dict] = field(default_factory=list)
    entities_touched: list[dict] = field(default_factory=list)


@dataclass
class SessionSummary:
    """Result of session synthesis."""
    session_id: str
    summary: str
    decisions: list[str] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class SessionEndSynthesizer:
    """
    AI synthesis at session end.

    Reviews all captured and processed data to generate
    a comprehensive session summary with double-confirmation.
    """

    SYSTEM_PROMPT = """You are analyzing a coding session transcript.
Extract the following in a structured format:

Summary: A 2-3 sentence summary of what was accomplished.
Decisions: Key technical decisions made (one per line, prefixed with "- ")
Learnings: Important discoveries or gotchas (one per line, prefixed with "- ")
Unresolved: Problems or blockers not yet resolved (one per line, prefixed with "- ")

Be specific and actionable. Focus on what matters for future sessions.
Skip routine operations like reading files or running commands."""

    OPUS_SYSTEM = """You are a senior software architect analyzing a coding session.
Provide deep analysis of:

Summary: A thorough 3-4 sentence summary of the session's accomplishments and context.
Decisions: Key technical decisions with their reasoning (one per line, prefixed with "- ")
Learnings: Important discoveries, gotchas, and insights (one per line, prefixed with "- ")
Patterns: Recurring themes or approaches observed (one per line, prefixed with "- ")
Unresolved: Outstanding issues requiring attention (one per line, prefixed with "- ")

Be thorough but concise. Focus on architectural implications and knowledge worth preserving."""

    async def synthesize(
        self,
        event_store: "SessionEventStore",
        graph_store: Any,
        client: "ClaudeClient",
    ) -> SessionSummary | None:
        """
        Generate session synthesis.

        Args:
            event_store: Store with session events
            graph_store: Graph store for persistence
            client: API client

        Returns:
            SessionSummary or None if disabled
        """
        if not client.enabled:
            return None

        # Build context
        context = self._build_context(event_store, graph_store)

        # Format prompt
        prompt = self._format_prompt(context)

        # Choose model based on intelligence level
        if client.config.intelligence_level == "ULTRA":
            response = await client.call_opus(prompt, system=self.OPUS_SYSTEM)
        else:
            response = await client.call_sonnet(prompt, system=self.SYSTEM_PROMPT)

        if not response:
            return None

        # Parse response
        summary = self._parse_response(response, event_store.session_id)

        # Double-confirm decisions
        await self._confirm_decisions(summary, graph_store)

        # Store summary
        try:
            if hasattr(graph_store, 'add_session_summary'):
                graph_store.add_session_summary({
                    "session_id": summary.session_id,
                    "summary": summary.summary,
                    "decisions": summary.decisions,
                    "learnings": summary.learnings,
                    "unresolved": summary.unresolved,
                    "timestamp": summary.timestamp.isoformat(),
                })
        except Exception:
            logger.debug("Failed to store session summary", exc_info=True)

        return summary

    def _build_context(
        self,
        event_store: "SessionEventStore",
        graph_store: Any,
    ) -> SessionContext:
        """Build context for AI synthesis."""
        # Get recent graph data
        memories = []
        decisions = []
        entities = []

        try:
            if hasattr(graph_store, 'get_recent_memories'):
                memories = graph_store.get_recent_memories(hours=2)
        except Exception:
            pass

        try:
            if hasattr(graph_store, 'get_recent_decisions'):
                decisions = graph_store.get_recent_decisions(hours=2)
        except Exception:
            pass

        try:
            if hasattr(graph_store, 'get_recent_entities'):
                entities = graph_store.get_recent_entities(hours=2)
        except Exception:
            pass

        return SessionContext(
            events=event_store.events,
            memories_added=memories,
            decisions_made=decisions,
            entities_touched=entities,
        )

    def _format_prompt(self, context: SessionContext) -> str:
        """Format context into prompt."""
        lines = ["# Session Transcript\n"]

        # Add events
        for event in context.events:
            if isinstance(event, (UserMessageEvent, AssistantMessageEvent)):
                content = event.content[:200] if event.content else ""
                if content:
                    lines.append(f"- {content}")
            elif hasattr(event, "tool_name"):
                lines.append(f"- [Tool: {event.tool_name}]")

        # Add already-extracted data
        if context.decisions_made:
            lines.append("\n# Decisions Already Recorded")
            for d in context.decisions_made[:5]:
                action = d.get('action', '')[:100] if isinstance(d, dict) else str(d)[:100]
                lines.append(f"- {action}")

        if context.memories_added:
            lines.append("\n# Memories Added This Session")
            for m in context.memories_added[:5]:
                content = m.get('content', '')[:100] if isinstance(m, dict) else str(m)[:100]
                lines.append(f"- {content}")

        return "\n".join(lines)

    def _parse_response(self, response: str, session_id: str) -> SessionSummary:
        """Parse AI response into SessionSummary."""
        summary = ""
        decisions: list[str] = []
        learnings: list[str] = []
        unresolved: list[str] = []

        current_section = None
        for line in response.split("\n"):
            line = line.strip()

            if line.lower().startswith("summary:"):
                current_section = "summary"
                summary = line[8:].strip()
            elif line.lower().startswith("decisions:"):
                current_section = "decisions"
            elif line.lower().startswith("learnings:"):
                current_section = "learnings"
            elif line.lower().startswith("unresolved:"):
                current_section = "unresolved"
            elif line.lower().startswith("patterns:"):
                current_section = "learnings"  # Merge patterns into learnings
            elif line.startswith("- "):
                item = line[2:].strip()
                if current_section == "decisions":
                    decisions.append(item)
                elif current_section == "learnings":
                    learnings.append(item)
                elif current_section == "unresolved":
                    unresolved.append(item)
            elif current_section == "summary" and line:
                summary += " " + line

        return SessionSummary(
            session_id=session_id,
            summary=summary.strip(),
            decisions=decisions,
            learnings=learnings,
            unresolved=unresolved,
        )

    async def _confirm_decisions(
        self,
        summary: SessionSummary,
        graph_store: Any,
    ) -> None:
        """Double-confirm decisions from summary."""
        for decision_text in summary.decisions:
            try:
                if not hasattr(graph_store, 'find_similar_decision'):
                    continue

                # Check if similar decision exists
                existing = graph_store.find_similar_decision(decision_text)
                if existing:
                    # Increment confirmation count
                    if hasattr(graph_store, 'update_decision'):
                        existing["confirmed"] = True
                        existing["confirmation_count"] = existing.get("confirmation_count", 0) + 1
                        graph_store.update_decision(existing)
                elif hasattr(graph_store, 'add_decision'):
                    # Add as new decision
                    graph_store.add_decision({
                        "action": decision_text,
                        "reasoning": f"Extracted from session {summary.session_id}",
                        "alternatives": [],
                        "confidence": 0.8,
                    })
            except Exception:
                logger.debug(f"Failed to confirm decision: {decision_text}", exc_info=True)
