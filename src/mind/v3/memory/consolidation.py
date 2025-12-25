"""
Memory consolidation for Mind v3.

Converts episodic memories into semantic patterns:
- Groups similar memories
- Extracts common themes
- Creates generalized patterns
- "You did X three times" → "You prefer X"
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

from .working_memory import MemoryItem, MemoryType


@dataclass
class ConsolidationConfig:
    """Configuration for memory consolidation."""

    # Minimum occurrences to form a pattern
    min_occurrences: int = 3

    # Similarity threshold for grouping (0-1)
    similarity_threshold: float = 0.7

    # Minimum confidence for pattern (lower for easier pattern detection)
    min_confidence: float = 0.3


@dataclass
class ConsolidatedPattern:
    """A pattern extracted from multiple memories."""

    id: str
    description: str
    source_ids: list[str]
    confidence: float
    occurrences: int
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize pattern to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "source_ids": self.source_ids,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConsolidatedPattern:
        """Deserialize pattern from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            source_ids=data["source_ids"],
            confidence=data["confidence"],
            occurrences=data["occurrences"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


class MemoryConsolidator:
    """
    Consolidates episodic memories into semantic patterns.

    Uses keyword-based grouping to find recurring themes
    and extracts generalized patterns from similar memories.
    """

    def __init__(self, config: ConsolidationConfig | None = None):
        """
        Initialize consolidator.

        Args:
            config: Consolidation configuration
        """
        self.config = config or ConsolidationConfig()
        self._pattern_counter = 0

    def consolidate(
        self,
        items: Sequence[MemoryItem],
    ) -> list[ConsolidatedPattern]:
        """
        Consolidate memory items into patterns.

        Args:
            items: Memory items to consolidate

        Returns:
            List of extracted patterns
        """
        if not items:
            return []

        # Group by memory type first
        by_type: dict[MemoryType, list[MemoryItem]] = defaultdict(list)
        for item in items:
            by_type[item.memory_type].append(item)

        patterns = []

        # Process each type separately
        for memory_type, type_items in by_type.items():
            type_patterns = self._consolidate_group(type_items, memory_type)
            patterns.extend(type_patterns)

        return patterns

    def _consolidate_group(
        self,
        items: list[MemoryItem],
        memory_type: MemoryType,
    ) -> list[ConsolidatedPattern]:
        """Consolidate items of the same type."""
        if len(items) < self.config.min_occurrences:
            return []

        # Extract keywords from each item
        item_keywords: dict[str, set[str]] = {}
        for item in items:
            keywords = self._extract_keywords(item.content)
            item_keywords[item.id] = keywords

        # Find common keyword clusters
        clusters = self._cluster_by_keywords(items, item_keywords)

        patterns = []
        for cluster in clusters:
            if len(cluster) >= self.config.min_occurrences:
                pattern = self._create_pattern(cluster, memory_type)
                if pattern.confidence >= self.config.min_confidence:
                    patterns.append(pattern)

        return patterns

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract significant keywords from text."""
        # Lowercase and extract words
        text = text.lower()
        words = re.findall(r"\b[a-z]+\b", text)

        # Filter stopwords and short words
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "under", "again", "further", "then", "once",
            "here", "there", "when", "where", "why", "how", "all", "each",
            "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very",
            "can", "just", "and", "but", "or", "if", "this", "that",
            "these", "those", "it", "its", "i", "you", "we", "they",
        }

        keywords = {w for w in words if len(w) > 2 and w not in stopwords}
        return keywords

    def _cluster_by_keywords(
        self,
        items: list[MemoryItem],
        item_keywords: dict[str, set[str]],
    ) -> list[list[MemoryItem]]:
        """Cluster items by keyword similarity."""
        # Find most common keywords
        all_keywords: Counter[str] = Counter()
        for keywords in item_keywords.values():
            all_keywords.update(keywords)

        # Focus on keywords that appear multiple times
        significant_keywords = {
            kw for kw, count in all_keywords.items()
            if count >= self.config.min_occurrences
        }

        if not significant_keywords:
            return []

        # Cluster by significant keywords
        clusters: dict[str, list[MemoryItem]] = defaultdict(list)

        for item in items:
            keywords = item_keywords[item.id]
            matching = keywords & significant_keywords

            if matching:
                # Use the most common matching keyword as cluster key
                best_kw = max(matching, key=lambda k: all_keywords[k])
                clusters[best_kw].append(item)

        return list(clusters.values())

    def _create_pattern(
        self,
        items: list[MemoryItem],
        memory_type: MemoryType,
    ) -> ConsolidatedPattern:
        """Create a pattern from clustered items."""
        self._pattern_counter += 1

        # Extract common keywords
        all_keywords: Counter[str] = Counter()
        for item in items:
            keywords = self._extract_keywords(item.content)
            all_keywords.update(keywords)

        # Get top keywords
        top_keywords = [kw for kw, _ in all_keywords.most_common(3)]

        # Generate description
        description = self._generate_description(top_keywords, memory_type, len(items))

        # Calculate confidence based on:
        # - Number of occurrences
        # - Average importance of source items
        avg_importance = sum(item.importance for item in items) / len(items)
        occurrence_boost = min(1.0, len(items) / 10)  # Max boost at 10 occurrences
        confidence = (avg_importance * 0.5 + occurrence_boost * 0.5)

        return ConsolidatedPattern(
            id=f"pattern-{self._pattern_counter}",
            description=description,
            source_ids=[item.id for item in items],
            confidence=confidence,
            occurrences=len(items),
            metadata={
                "memory_type": memory_type.value,
                "keywords": top_keywords,
            },
        )

    def _generate_description(
        self,
        keywords: list[str],
        memory_type: MemoryType,
        count: int,
    ) -> str:
        """Generate human-readable pattern description."""
        kw_str = ", ".join(keywords) if keywords else "unspecified"

        if memory_type == MemoryType.DECISION:
            return f"Recurring preference: {kw_str} (observed {count} times)"
        elif memory_type == MemoryType.LEARNING:
            return f"Common learning: {kw_str} (noted {count} times)"
        elif memory_type == MemoryType.EVENT:
            return f"Frequent activity: {kw_str} (occurred {count} times)"
        else:
            return f"Pattern: {kw_str} ({count} occurrences)"
