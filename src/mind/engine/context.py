"""Context retrieval engine with relevance scoring."""

import math
from datetime import datetime
from typing import Any, Optional

from mind.models.base import EntityType
from mind.storage.embeddings import EmbeddingStore
from mind.storage.sqlite import SQLiteStorage


# Scoring configuration
RECENCY_HALF_LIFE_DAYS = 7  # Recency boost halves every 7 days
MAX_RECENCY_BOOST = 0.3
MAX_FREQUENCY_BOOST = 0.2
MAX_TRIGGER_BOOST = 0.2


class ContextEngine:
    """Intelligent context retrieval combining semantic search with relevance scoring.

    Scoring formula:
        final_score = semantic_similarity * (1 + recency_boost + frequency_boost + trigger_boost)

    Where:
        - semantic_similarity: 0.0-1.0 from ChromaDB cosine distance
        - recency_boost: 0.0-0.3 based on entity age (newer = higher)
        - frequency_boost: 0.0-0.2 based on access count (logarithmic)
        - trigger_boost: 0.0-0.2 for exact phrase matches in document
    """

    def __init__(
        self,
        embedding_store: EmbeddingStore,
        storage: Optional[SQLiteStorage] = None,
    ):
        self.embeddings = embedding_store
        self.storage = storage

    async def get_relevant_context(
        self,
        query: str,
        project_id: str,
        entity_types: Optional[list[EntityType]] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get relevant context for a query with intelligent scoring.

        Combines semantic similarity with recency, access frequency,
        and trigger phrase matching for optimal relevance ranking.

        Args:
            query: Search query text
            project_id: Filter to specific project
            entity_types: Filter to specific entity types
            limit: Maximum results to return

        Returns:
            List of results sorted by final_score (highest first)
        """
        # Get semantic search results (fetch extra to allow filtering)
        results = await self.embeddings.search(
            query=query,
            entity_types=entity_types,
            project_id=project_id,
            limit=limit * 2,
        )

        if not results:
            return []

        # Collect entity IDs by type for batch lookups
        ids_by_type: dict[str, list[str]] = {}
        all_ids: list[str] = []
        for result in results:
            entity_type = result["entity_type"]
            entity_id = result["entity_id"]
            ids_by_type.setdefault(entity_type, []).append(entity_id)
            all_ids.append(entity_id)

        # Fetch access stats and timestamps if storage available
        access_stats: dict[str, dict[str, Any]] = {}
        timestamps: dict[str, datetime] = {}

        if self.storage:
            # Get access stats for all entities
            access_stats = await self.storage.get_access_stats(all_ids)

            # Get timestamps by entity type
            for entity_type, ids in ids_by_type.items():
                type_timestamps = await self.storage.get_entity_timestamps(entity_type, ids)
                timestamps.update(type_timestamps)

        # Apply combined scoring
        now = datetime.utcnow()
        scored_results = []

        for result in results:
            entity_id = result["entity_id"]
            semantic_score = result["similarity"]

            # Calculate recency boost
            recency_boost = 0.0
            if entity_id in timestamps:
                entity_time = timestamps[entity_id]
                days_old = (now - entity_time).days
                recency_boost = self._calculate_recency_boost(days_old)

            # Calculate frequency boost
            frequency_boost = 0.0
            if entity_id in access_stats:
                access_count = access_stats[entity_id]["access_count"]
                frequency_boost = self._calculate_frequency_boost(access_count)

            # Calculate trigger phrase boost
            trigger_boost = 0.0
            query_lower = query.lower()
            doc_lower = result.get("document", "").lower()
            if query_lower in doc_lower:
                trigger_boost = MAX_TRIGGER_BOOST

            # Combined score
            multiplier = 1 + recency_boost + frequency_boost + trigger_boost
            final_score = semantic_score * multiplier

            # Add scoring details to result
            result["final_score"] = final_score
            result["scoring"] = {
                "semantic": semantic_score,
                "recency_boost": recency_boost,
                "frequency_boost": frequency_boost,
                "trigger_boost": trigger_boost,
                "multiplier": multiplier,
            }

            scored_results.append(result)

        # Sort by final score (highest first)
        scored_results.sort(key=lambda x: x["final_score"], reverse=True)

        return scored_results[:limit]

    def _calculate_recency_boost(self, days_old: int) -> float:
        """Calculate recency boost using exponential decay.

        Args:
            days_old: Number of days since entity was created/updated

        Returns:
            Boost value between 0.0 and MAX_RECENCY_BOOST
        """
        if days_old < 0:
            days_old = 0
        # Exponential decay: boost = max_boost * 0.5^(days/half_life)
        decay = 0.5 ** (days_old / RECENCY_HALF_LIFE_DAYS)
        return MAX_RECENCY_BOOST * decay

    def _calculate_frequency_boost(self, access_count: int) -> float:
        """Calculate frequency boost using logarithmic scaling.

        Args:
            access_count: Number of times entity has been accessed

        Returns:
            Boost value between 0.0 and MAX_FREQUENCY_BOOST
        """
        if access_count <= 0:
            return 0.0
        # Logarithmic scaling: boost = 0.1 * log2(1 + count), capped at max
        boost = 0.1 * math.log2(1 + access_count)
        return min(MAX_FREQUENCY_BOOST, boost)
