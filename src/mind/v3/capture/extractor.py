"""
Transcript event extraction for Mind v3.

Extracts structured events from Claude Code conversation transcripts.
This is Layer 1 (local) extraction using regex and heuristics.
AI-powered extraction (Layer 2) enhances these results.
"""
from __future__ import annotations

import re
from typing import Any

from .events import (
    Event,
    EventType,
    ToolCallEvent,
    ToolResultEvent,
    UserMessageEvent,
    AssistantMessageEvent,
    DecisionEvent,
)


# Keywords that indicate a decision was made
DECISION_PATTERNS = [
    r"\bdecided\s+to\b",
    r"\bchose\s+to\b",
    r"\bgoing\s+with\b",
    r"\bwent\s+with\b",
    r"\bsettled\s+on\b",
    r"\bI'll\s+use\b",
    r"\blet's\s+use\b",
    r"\bI'm\s+going\s+with\b",
]

# Keywords that indicate reasoning
REASONING_PATTERNS = [
    r"\bbecause\b",
    r"\bsince\b",
    r"\bdue\s+to\b",
    r"\bfor\s+this\s+reason\b",
    r"\bas\s+it\b",
]

# Minimum length for a valid decision statement
MIN_DECISION_LENGTH = 15


class TranscriptExtractor:
    """
    Extracts events from Claude Code transcript turns.

    This is the local (Layer 1) extraction using regex and heuristics.
    AI-powered extraction (Layer 2) enhances these results.
    """

    def __init__(self):
        """Initialize extractor with compiled patterns."""
        self.decision_patterns = [
            re.compile(p, re.IGNORECASE) for p in DECISION_PATTERNS
        ]
        self.reasoning_patterns = [
            re.compile(p, re.IGNORECASE) for p in REASONING_PATTERNS
        ]

    def extract_from_turn(self, turn: dict[str, Any]) -> list[Event]:
        """
        Extract events from a single conversation turn.

        Args:
            turn: Conversation turn with 'role' and 'content'

        Returns:
            List of extracted events
        """
        events: list[Event] = []
        role = turn.get("role", "")
        content = turn.get("content", "")

        if role == "user":
            events.extend(self._extract_user_events(content))
        elif role == "assistant":
            events.extend(self._extract_assistant_events(content))

        return events

    def _extract_user_events(self, content: Any) -> list[Event]:
        """Extract events from user message."""
        events = []

        if isinstance(content, str):
            events.append(UserMessageEvent(content=content))
        elif isinstance(content, list):
            # Handle structured content
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            if text_parts:
                events.append(UserMessageEvent(content=" ".join(text_parts)))

        return events

    def _extract_assistant_events(self, content: Any) -> list[Event]:
        """Extract events from assistant message."""
        events = []

        if isinstance(content, str):
            # Text response
            events.append(AssistantMessageEvent(content=content))
            events.extend(self._detect_decisions(content))

        elif isinstance(content, list):
            # Structured content with tool calls
            text_parts = []

            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "tool_use":
                        events.append(ToolCallEvent(
                            tool_name=part.get("name", "unknown"),
                            tool_input=part.get("input", {}),
                        ))
                    elif part.get("type") == "tool_result":
                        events.append(ToolResultEvent(
                            tool_name=part.get("name", "unknown"),
                            success=not part.get("is_error", False),
                            result=part.get("content"),
                            error=part.get("content") if part.get("is_error") else None,
                        ))
                    elif part.get("type") == "text":
                        text_parts.append(part.get("text", ""))

            if text_parts:
                full_text = " ".join(text_parts)
                events.append(AssistantMessageEvent(content=full_text))
                events.extend(self._detect_decisions(full_text))

        return events

    def _detect_decisions(self, text: str) -> list[DecisionEvent]:
        """
        Detect decision statements in text using keyword patterns.

        This is basic heuristic detection. AI extraction improves on this.
        """
        decisions = []
        seen_sentences = set()

        for pattern in self.decision_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                # Extract sentence containing the decision
                start = max(0, text.rfind(".", 0, match.start()) + 1)
                end = text.find(".", match.end())
                if end == -1:
                    end = len(text)

                sentence = text[start:end].strip()

                # Skip if too short or already seen
                if len(sentence) < MIN_DECISION_LENGTH:
                    continue
                if sentence in seen_sentences:
                    continue
                seen_sentences.add(sentence)

                # Try to extract reasoning
                reasoning = ""
                for r_pattern in self.reasoning_patterns:
                    r_match = r_pattern.search(sentence)
                    if r_match:
                        reasoning = sentence[r_match.start():].strip()
                        break

                decisions.append(DecisionEvent(
                    action=sentence[:500],  # Truncate if too long
                    reasoning=reasoning[:1000],
                    confidence=0.5,  # Low confidence for heuristic detection
                ))

        return decisions

    def extract_from_transcript(self, transcript: list[dict[str, Any]]) -> list[Event]:
        """
        Extract all events from a full transcript.

        Args:
            transcript: List of conversation turns

        Returns:
            List of all extracted events
        """
        all_events = []

        for turn in transcript:
            events = self.extract_from_turn(turn)
            all_events.extend(events)

        return all_events
