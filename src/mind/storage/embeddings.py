"""ChromaDB embedding storage for semantic search."""

import logging
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings

from mind.models.base import EntityType

logger = logging.getLogger(__name__)

# Embedding model - MiniLM is small (~90MB) and fast
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class EmbeddingStore:
    """ChromaDB-based embedding storage for semantic search."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "chroma"
        self._client: Optional[chromadb.Client] = None
        self._collections: dict[str, chromadb.Collection] = {}

    def initialize(self) -> None:
        """Initialize ChromaDB client and collections."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Use persistent client with local storage
        self._client = chromadb.PersistentClient(
            path=str(self.data_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Create collections for each searchable entity type
        for entity_type in [EntityType.DECISION, EntityType.ISSUE, EntityType.SHARP_EDGE, EntityType.EPISODE]:
            collection_name = f"mind_{entity_type.value}"
            self._collections[entity_type.value] = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        logger.info("ChromaDB initialized with %d collections", len(self._collections))

    @property
    def client(self) -> chromadb.Client:
        """Get ChromaDB client."""
        if self._client is None:
            raise RuntimeError("EmbeddingStore not initialized. Call initialize() first.")
        return self._client

    def _get_collection(self, entity_type: EntityType) -> chromadb.Collection:
        """Get collection for entity type."""
        collection = self._collections.get(entity_type.value)
        if collection is None:
            raise ValueError(f"No collection for entity type: {entity_type}")
        return collection

    async def add_embedding(
        self,
        entity_type: EntityType,
        entity_id: str,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Add or update embedding for an entity."""
        collection = self._get_collection(entity_type)

        # Prepare metadata
        meta = metadata or {}
        meta["entity_type"] = entity_type.value

        # Upsert document (ChromaDB will generate embedding)
        collection.upsert(
            ids=[entity_id],
            documents=[text],
            metadatas=[meta],
        )

        logger.debug("Added embedding for %s: %s", entity_type.value, entity_id)

    async def remove_embedding(
        self,
        entity_type: EntityType,
        entity_id: str,
    ) -> None:
        """Remove embedding for an entity."""
        collection = self._get_collection(entity_type)
        collection.delete(ids=[entity_id])
        logger.debug("Removed embedding for %s: %s", entity_type.value, entity_id)

    async def search(
        self,
        query: str,
        entity_types: Optional[list[EntityType]] = None,
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for similar entities across collections.

        Args:
            query: Search query text
            entity_types: Filter to specific entity types (default: all)
            project_id: Filter to specific project
            limit: Maximum results per entity type

        Returns:
            List of results with entity_id, entity_type, distance, and metadata
        """
        if entity_types is None:
            entity_types = [EntityType.DECISION, EntityType.ISSUE, EntityType.SHARP_EDGE, EntityType.EPISODE]

        results: list[dict[str, Any]] = []

        for entity_type in entity_types:
            try:
                collection = self._get_collection(entity_type)

                # Build where clause for project filtering
                where: Optional[dict[str, Any]] = None
                if project_id:
                    # For sharp edges, include global (no project_id) and project-specific
                    if entity_type == EntityType.SHARP_EDGE:
                        where = {
                            "$or": [
                                {"project_id": project_id},
                                {"project_id": {"$exists": False}},
                            ]
                        }
                    else:
                        where = {"project_id": project_id}

                # Query collection
                query_results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=where,
                    include=["distances", "metadatas", "documents"],
                )

                # Process results
                if query_results["ids"] and query_results["ids"][0]:
                    for i, entity_id in enumerate(query_results["ids"][0]):
                        distance = query_results["distances"][0][i] if query_results["distances"] else 0
                        metadata = query_results["metadatas"][0][i] if query_results["metadatas"] else {}
                        document = query_results["documents"][0][i] if query_results["documents"] else ""

                        results.append({
                            "entity_id": entity_id,
                            "entity_type": entity_type.value,
                            "distance": distance,
                            "similarity": 1 - distance,  # Cosine distance to similarity
                            "metadata": metadata,
                            "document": document,
                        })

            except Exception as e:
                logger.warning("Error searching %s: %s", entity_type.value, e)
                continue

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:limit]

    async def search_by_trigger_phrases(
        self,
        query: str,
        entity_types: Optional[list[EntityType]] = None,
        project_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search for entities with matching trigger phrases.

        This is a faster exact-match search for trigger phrases.
        """
        # For now, delegate to semantic search
        # In future, could use a separate index for trigger phrases
        return await self.search(
            query=query,
            entity_types=entity_types,
            project_id=project_id,
            limit=5,
        )

    def reset(self) -> None:
        """Reset all collections (for testing)."""
        if self._client:
            self._client.reset()
            self._collections.clear()


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

            # Boost for exact trigger phrase matches (future: check actual phrases)
            query_lower = query.lower()
            doc_lower = result.get("document", "").lower()
            if query_lower in doc_lower:
                score *= 1.2

            result["final_score"] = score
            scored_results.append(result)

        # Sort by final score and return top results
        scored_results.sort(key=lambda x: x["final_score"], reverse=True)
        return scored_results[:limit]
