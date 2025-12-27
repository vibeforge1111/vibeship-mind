"""
Decision extraction for Mind v3.

Extracts decision statements from text using:
- Local: Regex patterns and heuristics
- API: Claude/GPT for deeper understanding (future)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from mind.v3.intelligence.cascade import ModelTier, ExtractionResult


# Decision indicator patterns
DECISION_PATTERNS = [
    r"\b(I\s+)?decided\s+to\b",
    r"\b(I\s+)?chose\s+to\b",
    r"\b(I'm|I\s+am)\s+going\s+with\b",
    r"\bwent\s+with\b",
    r"\bsettled\s+on\b",
    r"\blet's\s+use\b",
    r"\bI'll\s+use\b",
    r"\busing\b(?=.*\b(instead|rather|over)\b)",
]

# Reasoning indicator patterns
REASONING_PATTERNS = [
    r"\bbecause\b",
    r"\bsince\b",
    r"\bdue\s+to\b",
    r"\bfor\s+this\s+reason\b",
    r"\bas\s+it\b",
    r"\bso\s+that\b",
]

# Alternative indicator patterns
ALTERNATIVE_PATTERNS = [
    r"\binstead\s+of\b",
    r"\brather\s+than\b",
    r"\bover\b",
    r"\bnot\s+using\b",
]

# Minimum length for a valid decision
MIN_DECISION_LENGTH = 15


@dataclass
class Decision:
    """Represents an extracted decision."""

    action: str
    reasoning: str = ""
    confidence: float = 0.0
    alternatives: list[str] = field(default_factory=list)
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "context": self.context,
        }


class LocalDecisionExtractor:
    """
    Extracts decisions using regex patterns and heuristics.

    This is Tier 1 (local) extraction - free and instant.
    For deeper understanding, escalate to API tiers.
    """

    def __init__(self):
        """Initialize with compiled patterns."""
        self.decision_patterns = [
            re.compile(p, re.IGNORECASE) for p in DECISION_PATTERNS
        ]
        self.reasoning_patterns = [
            re.compile(p, re.IGNORECASE) for p in REASONING_PATTERNS
        ]
        self.alternative_patterns = [
            re.compile(p, re.IGNORECASE) for p in ALTERNATIVE_PATTERNS
        ]

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract decisions from text.

        Args:
            text: Text to extract decisions from

        Returns:
            ExtractionResult with decisions and confidence
        """
        decisions = self._find_decisions(text)

        # Calculate overall confidence
        if not decisions:
            confidence = 0.0
        else:
            # Average confidence of found decisions
            confidence = sum(d.confidence for d in decisions) / len(decisions)

        return ExtractionResult(
            content={
                "decisions": [d.to_dict() for d in decisions],
            },
            confidence=confidence,
            tier_used=ModelTier.LOCAL,
            model_name="regex",
            metadata={
                "pattern_count": len(decisions),
            },
        )

    def _find_decisions(self, text: str) -> list[Decision]:
        """Find all decision statements in text."""
        decisions = []
        seen_sentences = set()

        for pattern in self.decision_patterns:
            for match in pattern.finditer(text):
                # Extract the sentence containing the decision
                sentence = self._extract_sentence(text, match.start(), match.end())

                # Skip if too short or already seen
                if len(sentence) < MIN_DECISION_LENGTH:
                    continue
                if sentence in seen_sentences:
                    continue
                seen_sentences.add(sentence)

                # Extract components
                reasoning = self._extract_reasoning(sentence)
                alternatives = self._extract_alternatives(sentence)

                # Calculate confidence for this decision
                confidence = self._calculate_confidence(sentence, reasoning, alternatives)

                decisions.append(Decision(
                    action=sentence[:500],  # Truncate if too long
                    reasoning=reasoning[:1000],
                    confidence=confidence,
                    alternatives=alternatives,
                ))

        return decisions

    def _extract_sentence(self, text: str, match_start: int, match_end: int) -> str:
        """Extract the sentence containing a match."""
        # Find sentence boundaries
        start = text.rfind(".", 0, match_start)
        start = start + 1 if start != -1 else 0

        end = text.find(".", match_end)
        end = end + 1 if end != -1 else len(text)

        return text[start:end].strip()

    def _extract_reasoning(self, sentence: str) -> str:
        """Extract reasoning from a decision sentence."""
        for pattern in self.reasoning_patterns:
            match = pattern.search(sentence)
            if match:
                # Return text from the reasoning keyword onward
                return sentence[match.start():].strip()
        return ""

    def _extract_alternatives(self, sentence: str) -> list[str]:
        """Extract mentioned alternatives from a decision sentence."""
        alternatives = []

        for pattern in self.alternative_patterns:
            match = pattern.search(sentence)
            if match:
                # Extract the word/phrase after the pattern
                after = sentence[match.end():].strip()
                # Get first word or phrase (up to punctuation or conjunction)
                alt_match = re.match(r"[\w\s-]+", after)
                if alt_match:
                    alt = alt_match.group().strip()
                    if alt and len(alt) > 2:  # Filter very short matches
                        alternatives.append(alt)

        return alternatives

    def _calculate_confidence(
        self,
        sentence: str,
        reasoning: str,
        alternatives: list[str],
    ) -> float:
        """
        Calculate confidence score for a decision.

        Factors:
        - Base confidence for pattern match: 0.4
        - Has reasoning: +0.2
        - Has alternatives: +0.1
        - Sentence length (more context): +0.1
        - Contains specific technology/tool: +0.1
        """
        confidence = 0.4  # Base confidence for pattern match

        # Reasoning adds confidence
        if reasoning:
            confidence += 0.2

        # Alternatives add confidence
        if alternatives:
            confidence += 0.1

        # Longer sentences usually have more context
        if len(sentence) > 50:
            confidence += 0.1

        # Technical terms suggest concrete decision
        tech_patterns = [
            r"\b(python|javascript|typescript|rust|go)\b",
            r"\b(react|vue|angular|svelte)\b",
            r"\b(postgres|mysql|sqlite|mongodb|redis)\b",
            r"\b(aws|gcp|azure|docker|kubernetes)\b",
            r"\b(rest|graphql|grpc)\b",
        ]
        for pattern in tech_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                confidence += 0.1
                break

        # Cap at 0.9 for local extraction (leave room for API to add certainty)
        return min(confidence, 0.9)
