"""
Local intelligence handlers for Mind v3.

Provides regex and rule-based extraction that runs locally with no API calls.
These are the Tier 1 (LOCAL) handlers - free, instant, and always available.
"""
from __future__ import annotations

import re
from typing import Any

from .extractors.decision import LocalDecisionExtractor
from .extractors.entity import LocalEntityExtractor


# Singleton extractors
_decision_extractor: LocalDecisionExtractor | None = None
_entity_extractor: LocalEntityExtractor | None = None


def _get_decision_extractor() -> LocalDecisionExtractor:
    """Get or create the decision extractor."""
    global _decision_extractor
    if _decision_extractor is None:
        _decision_extractor = LocalDecisionExtractor()
    return _decision_extractor


def _get_entity_extractor() -> LocalEntityExtractor:
    """Get or create the entity extractor."""
    global _entity_extractor
    if _entity_extractor is None:
        _entity_extractor = LocalEntityExtractor()
    return _entity_extractor


def extract_decisions_local(text: str, **kwargs: Any) -> dict[str, Any]:
    """
    Extract decisions using regex patterns.

    This is a LOCAL level handler - no API calls, instant results.

    Args:
        text: Text to extract decisions from
        **kwargs: Additional options (unused)

    Returns:
        Dict with decisions, confidence, and metadata
    """
    extractor = _get_decision_extractor()
    result = extractor.extract(text)

    return {
        "content": result.content,
        "confidence": result.confidence,
        "handler_name": "local_decision_regex",
        "metadata": result.metadata,
    }


def extract_entities_local(text: str, **kwargs: Any) -> dict[str, Any]:
    """
    Extract entities using regex patterns.

    This is a LOCAL level handler - no API calls, instant results.

    Args:
        text: Text to extract entities from
        **kwargs: Additional options (unused)

    Returns:
        Dict with entities, confidence, and metadata
    """
    extractor = _get_entity_extractor()
    result = extractor.extract(text)

    return {
        "content": result.content,
        "confidence": result.confidence,
        "handler_name": "local_entity_regex",
        "metadata": result.metadata,
    }


# Pattern extraction keywords and their types
PATTERN_KEYWORDS = {
    # Preferences
    "prefer": "preference",
    "like to": "preference",
    "always use": "preference",
    "favor": "preference",

    # Habits
    "always": "habit",
    "usually": "habit",
    "typically": "habit",
    "tend to": "habit",
    "habit": "habit",

    # Avoidances
    "avoid": "avoidance",
    "never": "avoidance",
    "don't like": "avoidance",
    "hate": "avoidance",

    # Blind spots
    "forget to": "blind_spot",
    "overlook": "blind_spot",
    "miss": "blind_spot",
    "often forget": "blind_spot",
}


def extract_patterns_local(text: str, **kwargs: Any) -> dict[str, Any]:
    """
    Extract patterns using regex and keyword matching.

    This is a LOCAL level handler - no API calls, instant results.

    Looks for:
    - Preference statements ("I prefer...", "I like to...")
    - Habit indicators ("I always...", "I usually...")
    - Avoidance patterns ("I avoid...", "I never...")
    - Blind spot indicators ("I often forget...", "I overlook...")

    Args:
        text: Text to extract patterns from
        **kwargs: Additional options (unused)

    Returns:
        Dict with patterns, confidence, and metadata
    """
    patterns = []
    seen = set()

    # Check for each keyword pattern
    for keyword, pattern_type in PATTERN_KEYWORDS.items():
        # Build pattern to capture the context around the keyword
        regex = re.compile(
            rf"((?:I|we|user)\s+)?{re.escape(keyword)}\s+([^.!?\n]+)",
            re.IGNORECASE,
        )

        for match in regex.finditer(text):
            full_match = match.group(0).strip()

            # Skip if too short or already seen
            if len(full_match) < 10 or full_match.lower() in seen:
                continue
            seen.add(full_match.lower())

            # Calculate confidence based on context
            confidence = _calculate_pattern_confidence(full_match, keyword)

            patterns.append({
                "description": full_match[:200],  # Truncate long matches
                "pattern_type": pattern_type,
                "confidence": confidence,
                "keyword": keyword,
            })

    # Sort by confidence
    patterns.sort(key=lambda p: p["confidence"], reverse=True)

    # Overall confidence
    if not patterns:
        overall_confidence = 0.0
    else:
        overall_confidence = sum(p["confidence"] for p in patterns) / len(patterns)

    return {
        "content": {"patterns": patterns},
        "confidence": overall_confidence,
        "handler_name": "local_pattern_regex",
        "metadata": {
            "pattern_count": len(patterns),
            "types_found": list(set(p["pattern_type"] for p in patterns)),
        },
    }


def _calculate_pattern_confidence(text: str, keyword: str) -> float:
    """
    Calculate confidence for a pattern match.

    Factors:
    - Base confidence for keyword match: 0.4
    - First person ("I", "we"): +0.15
    - Context length (more context = more reliable): +0.15
    - Contains specific tool/tech: +0.1
    - Strong indicator words: +0.1
    """
    confidence = 0.4

    # First person increases confidence
    if re.search(r"\b(I|we|my|our)\b", text, re.IGNORECASE):
        confidence += 0.15

    # Longer context is more reliable
    if len(text) > 30:
        confidence += 0.1
    if len(text) > 50:
        confidence += 0.05

    # Technical terms suggest concrete pattern
    tech_terms = [
        r"\b(python|javascript|typescript|rust|go)\b",
        r"\b(react|vue|angular|svelte)\b",
        r"\b(tests?|testing|TDD|BDD)\b",
        r"\b(git|commit|branch|merge)\b",
        r"\b(function|class|method|variable)\b",
    ]
    for pattern in tech_terms:
        if re.search(pattern, text, re.IGNORECASE):
            confidence += 0.1
            break

    # Strong indicator words
    strong_indicators = ["always", "never", "every time", "consistently"]
    for indicator in strong_indicators:
        if indicator.lower() in text.lower():
            confidence += 0.1
            break

    # Cap at 0.85 for local extraction
    return min(confidence, 0.85)
