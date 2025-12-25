"""
Pattern detection for Mind v3.

Detects behavioral patterns from text:
- Preferences: Things the user prefers
- Habits: Things the user always/usually does
- Anti-patterns: Things the user avoids
- Blind spots: Things the user forgets or tends to miss
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mind.v3.intelligence.cascade import ModelTier, ExtractionResult


class PatternType(str, Enum):
    """Types of behavioral patterns."""

    PREFERENCE = "preference"
    HABIT = "habit"
    ANTI_PATTERN = "anti_pattern"
    BLIND_SPOT = "blind_spot"


# Pattern indicators by type
PREFERENCE_PATTERNS = [
    (r"\bI\s+prefer\b", 0.8),
    (r"\bI\s+like\s+to\b", 0.6),
    (r"\bI\s+favor\b", 0.7),
    (r"\bI\s+tend\s+to\s+choose\b", 0.6),
]

HABIT_PATTERNS = [
    (r"\bI\s+always\b", 0.9),
    (r"\bI\s+usually\b", 0.7),
    (r"\bI\s+typically\b", 0.7),
    (r"\bI\s+consistently\b", 0.8),
    (r"\bI\s+make\s+sure\s+to\b", 0.7),
    (r"\bI\s+never\b", 0.8),  # Never is a strong habit
]

ANTI_PATTERN_PATTERNS = [
    (r"\bI\s+avoid\b", 0.8),
    (r"\bI\s+don't\s+like\b", 0.6),
    (r"\bI\s+stay\s+away\s+from\b", 0.7),
    (r"\bI\s+try\s+not\s+to\b", 0.6),
]

BLIND_SPOT_PATTERNS = [
    (r"\bI\s+(?:often\s+)?forget\b", 0.8),
    (r"\bI\s+tend\s+to\s+(?:miss|overlook|skip)\b", 0.7),
    (r"\bI\s+sometimes\s+forget\b", 0.6),
    (r"\bI\s+tend\s+to\s+over", 0.7),  # over-engineer, over-complicate
    (r"\bI\s+have\s+trouble\b", 0.6),
]

# Minimum length for a valid pattern statement
MIN_PATTERN_LENGTH = 15


@dataclass
class Pattern:
    """Represents a detected behavioral pattern."""

    description: str
    pattern_type: PatternType
    confidence: float = 0.0
    evidence_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "type": self.pattern_type.value,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
        }


class LocalPatternDetector:
    """
    Detects behavioral patterns using regex.

    This is Tier 1 (local) detection - free and instant.
    For deeper pattern analysis, escalate to API tiers.
    """

    def __init__(self):
        """Initialize with compiled patterns."""
        self.pattern_groups = {
            PatternType.PREFERENCE: [
                (re.compile(p, re.IGNORECASE), conf)
                for p, conf in PREFERENCE_PATTERNS
            ],
            PatternType.HABIT: [
                (re.compile(p, re.IGNORECASE), conf)
                for p, conf in HABIT_PATTERNS
            ],
            PatternType.ANTI_PATTERN: [
                (re.compile(p, re.IGNORECASE), conf)
                for p, conf in ANTI_PATTERN_PATTERNS
            ],
            PatternType.BLIND_SPOT: [
                (re.compile(p, re.IGNORECASE), conf)
                for p, conf in BLIND_SPOT_PATTERNS
            ],
        }

    def extract(self, text: str) -> ExtractionResult:
        """
        Detect patterns from text.

        Args:
            text: Text to detect patterns from

        Returns:
            ExtractionResult with patterns and confidence
        """
        patterns = self._find_patterns(text)

        # Calculate overall confidence
        if not patterns:
            confidence = 0.0
        else:
            confidence = sum(p.confidence for p in patterns) / len(patterns)

        return ExtractionResult(
            content={
                "patterns": [p.to_dict() for p in patterns],
            },
            confidence=confidence,
            tier_used=ModelTier.LOCAL,
            model_name="regex",
            metadata={
                "pattern_count": len(patterns),
                "types_found": list(set(p.pattern_type.value for p in patterns)),
            },
        )

    def _find_patterns(self, text: str) -> list[Pattern]:
        """Find all patterns in text."""
        patterns = []
        seen_sentences = set()

        for pattern_type, pattern_list in self.pattern_groups.items():
            for regex, base_confidence in pattern_list:
                for match in regex.finditer(text):
                    # Extract the sentence containing the pattern
                    sentence = self._extract_sentence(text, match.start(), match.end())

                    # Skip if too short or already seen
                    if len(sentence) < MIN_PATTERN_LENGTH:
                        continue
                    if sentence in seen_sentences:
                        continue
                    seen_sentences.add(sentence)

                    # Calculate confidence
                    confidence = self._calculate_confidence(
                        sentence, base_confidence
                    )

                    patterns.append(Pattern(
                        description=sentence[:500],
                        pattern_type=pattern_type,
                        confidence=confidence,
                    ))

        return patterns

    def _extract_sentence(self, text: str, match_start: int, match_end: int) -> str:
        """Extract the sentence containing a match."""
        # Find sentence boundaries
        start = text.rfind(".", 0, match_start)
        start = start + 1 if start != -1 else 0

        end = text.find(".", match_end)
        end = end + 1 if end != -1 else len(text)

        return text[start:end].strip()

    def _calculate_confidence(
        self,
        sentence: str,
        base_confidence: float,
    ) -> float:
        """
        Calculate confidence score for a pattern.

        Factors:
        - Base confidence from pattern type
        - Sentence length (more context = higher confidence)
        - Contains specific examples/details
        """
        confidence = base_confidence

        # Longer sentences usually have more context
        if len(sentence) > 50:
            confidence += 0.05
        if len(sentence) > 100:
            confidence += 0.05

        # Contains specific technical terms
        tech_patterns = [
            r"\b(python|javascript|typescript|rust)\b",
            r"\b(function|class|method|variable)\b",
            r"\b(test|tests|testing)\b",
            r"\b(async|sync|promise)\b",
        ]
        for pattern in tech_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                confidence += 0.02
                break

        # Cap at 0.95 for local detection
        return min(confidence, 0.95)
