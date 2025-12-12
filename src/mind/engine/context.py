"""Context retrieval engine."""

from typing import Any, Optional

from mind.models.base import EntityType
from mind.storage.embeddings import EmbeddingStore


class ContextEngine:
    """Intelligent context retrieval combining semantic search with weighting."""

    def __init__(self, embedding_store: EmbeddingStore):
        self.embeddings = embedding_store

    async def get_relevant_context(
        self,
        query: str,
        project_id: str,
        entity_types: Optional[list[EntityType]] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get relevant context for a query with intelligent weighting.

        Combines:
        - Semantic similarity
        - Recency weighting
        - Trigger phrase matching
        """
        # Get semantic search results
        results = await self.embeddings.search(
            query=query,
            entity_types=entity_types,
            project_id=project_id,
            limit=limit * 2,  # Get more, then filter
        )

        # Apply additional scoring
        scored_results = []
        for result in results:
            score = result["similarity"]

            # Boost for exact trigger phrase matches
            query_lower = query.lower()
            doc_lower = result.get("document", "").lower()
            if query_lower in doc_lower:
                score *= 1.2

            result["final_score"] = score
            scored_results.append(result)

        # Sort by final score and return top results
        scored_results.sort(key=lambda x: x["final_score"], reverse=True)
        return scored_results[:limit]
