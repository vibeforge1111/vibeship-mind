"""
LanceDB graph store for Mind v3 context graph.

Provides vector storage and search for all graph node types:
- Decisions (with reasoning, alternatives, context)
- Entities (files, functions, concepts)
- Patterns (preferences, habits, blind spots)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

import lancedb
import pyarrow as pa

if TYPE_CHECKING:
    from ..retrieval.embeddings import EmbeddingService


# Embedding dimension (using small embeddings for now)
EMBED_DIM = 384

# Module-level embedding service (lazy initialized)
_embedding_service: "EmbeddingService | None" = None


def generate_id(prefix: str) -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _get_embedding_service() -> "EmbeddingService":
    """Get or create the shared embedding service."""
    global _embedding_service
    if _embedding_service is None:
        from ..retrieval.embeddings import EmbeddingService
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_embedding(text: str) -> list[float]:
    """
    Get embedding vector for text.

    Uses sentence-transformers when available, falls back to hash-based.
    """
    service = _get_embedding_service()
    return service.embed(text)


class GraphStore:
    """
    LanceDB-backed context graph store.

    Provides storage and vector search for:
    - Decisions
    - Entities
    - Patterns
    """

    def __init__(self, path: Path):
        """
        Initialize graph store.

        Args:
            path: Directory for LanceDB files
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

        self.db = lancedb.connect(str(self.path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Initialize all graph tables."""
        tables_response = self.db.list_tables()
        # Handle both old API (list) and new API (ListTablesResponse)
        if hasattr(tables_response, 'tables'):
            existing = set(tables_response.tables)
        else:
            existing = set(tables_response)

        # Decisions table
        if "decisions" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("action", pa.string()),
                pa.field("reasoning", pa.string()),
                pa.field("alternatives", pa.string()),  # JSON array
                pa.field("confidence", pa.float32()),
                pa.field("timestamp", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
            ])
            self.db.create_table("decisions", schema=schema)

        # Entities table
        if "entities" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("name", pa.string()),
                pa.field("type", pa.string()),
                pa.field("description", pa.string()),
                pa.field("properties", pa.string()),  # JSON object
                pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
            ])
            self.db.create_table("entities", schema=schema)

        # Patterns table
        if "patterns" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("description", pa.string()),
                pa.field("pattern_type", pa.string()),
                pa.field("confidence", pa.float32()),
                pa.field("evidence_count", pa.int32()),
                pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
            ])
            self.db.create_table("patterns", schema=schema)

        # Memories table (for v3 context retrieval)
        if "memories" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("memory_type", pa.string()),
                pa.field("timestamp", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
            ])
            self.db.create_table("memories", schema=schema)

    def is_initialized(self) -> bool:
        """Check if store is properly initialized."""
        required = {"decisions", "entities", "patterns", "memories"}
        tables_response = self.db.list_tables()
        if hasattr(tables_response, 'tables'):
            existing = set(tables_response.tables)
        else:
            existing = set(tables_response)
        return required.issubset(existing)

    def list_tables(self) -> list[str]:
        """List all tables in the store."""
        tables_response = self.db.list_tables()
        if hasattr(tables_response, 'tables'):
            return list(tables_response.tables)
        return list(tables_response)

    # =========================================================================
    # Decision operations
    # =========================================================================

    def add_decision(self, decision: dict[str, Any]) -> str:
        """
        Add a decision to the graph.

        Args:
            decision: Decision data with action, reasoning, etc.

        Returns:
            Generated decision ID
        """
        doc_id = generate_id("dec")

        action = decision.get("action", "")
        reasoning = decision.get("reasoning", "")
        alternatives = decision.get("alternatives", [])

        # Create embedding from action + reasoning
        embed_text = f"{action} {reasoning}"

        record = {
            "id": doc_id,
            "action": action,
            "reasoning": reasoning,
            "alternatives": json.dumps(alternatives),
            "confidence": float(decision.get("confidence", 0.0)),
            "timestamp": decision.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "vector": get_embedding(embed_text),
        }

        table = self.db.open_table("decisions")
        table.add([record])

        return doc_id

    def get_decision(self, doc_id: str) -> dict[str, Any] | None:
        """Get a decision by ID."""
        table = self.db.open_table("decisions")
        results = table.search().where(f"id = '{doc_id}'", prefilter=True).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "action": row["action"],
                "reasoning": row["reasoning"],
                "alternatives": json.loads(row["alternatives"]) if row["alternatives"] else [],
                "confidence": row["confidence"],
                "timestamp": row["timestamp"],
            }
        return None

    def search_decisions(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search decisions by text similarity.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching decisions
        """
        table = self.db.open_table("decisions")
        query_vector = get_embedding(query)

        results = table.search(query_vector).limit(limit).to_list()

        return [
            {
                "id": r["id"],
                "action": r["action"],
                "reasoning": r["reasoning"],
                "alternatives": json.loads(r["alternatives"]) if r["alternatives"] else [],
                "confidence": r["confidence"],
                "timestamp": r["timestamp"],
            }
            for r in results
        ]

    # =========================================================================
    # Entity operations
    # =========================================================================

    def add_entity(self, entity: dict[str, Any]) -> str:
        """Add an entity to the graph."""
        doc_id = generate_id("ent")

        name = entity.get("name", "")
        entity_type = entity.get("type", "unknown")
        description = entity.get("description", "")
        properties = entity.get("properties", {})

        # Create embedding from name + description
        embed_text = f"{name} {description}"

        record = {
            "id": doc_id,
            "name": name,
            "type": entity_type,
            "description": description,
            "properties": json.dumps(properties),
            "vector": get_embedding(embed_text),
        }

        table = self.db.open_table("entities")
        table.add([record])

        return doc_id

    def get_entity(self, doc_id: str) -> dict[str, Any] | None:
        """Get an entity by ID."""
        table = self.db.open_table("entities")
        results = table.search().where(f"id = '{doc_id}'", prefilter=True).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "description": row["description"],
                "properties": json.loads(row["properties"]) if row["properties"] else {},
            }
        return None

    def search_entities(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search entities by text similarity."""
        table = self.db.open_table("entities")
        query_vector = get_embedding(query)

        results = table.search(query_vector).limit(limit).to_list()

        return [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "description": r["description"],
                "properties": json.loads(r["properties"]) if r["properties"] else {},
            }
            for r in results
        ]

    # =========================================================================
    # Pattern operations
    # =========================================================================

    def add_pattern(self, pattern: dict[str, Any]) -> str:
        """Add a pattern to the graph."""
        doc_id = generate_id("pat")

        description = pattern.get("description", "")
        pattern_type = pattern.get("pattern_type", "unknown")

        record = {
            "id": doc_id,
            "description": description,
            "pattern_type": pattern_type,
            "confidence": float(pattern.get("confidence", 0.0)),
            "evidence_count": int(pattern.get("evidence_count", 0)),
            "vector": get_embedding(description),
        }

        table = self.db.open_table("patterns")
        table.add([record])

        return doc_id

    def get_pattern(self, doc_id: str) -> dict[str, Any] | None:
        """Get a pattern by ID."""
        table = self.db.open_table("patterns")
        results = table.search().where(f"id = '{doc_id}'", prefilter=True).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "description": row["description"],
                "pattern_type": row["pattern_type"],
                "confidence": row["confidence"],
                "evidence_count": row["evidence_count"],
            }
        return None

    def search_patterns(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search patterns by text similarity."""
        table = self.db.open_table("patterns")
        query_vector = get_embedding(query)

        results = table.search(query_vector).limit(limit).to_list()

        return [
            {
                "id": r["id"],
                "description": r["description"],
                "pattern_type": r["pattern_type"],
                "confidence": r["confidence"],
                "evidence_count": r["evidence_count"],
            }
            for r in results
        ]

    def update_pattern(
        self,
        doc_id: str,
        confidence: float | None = None,
        evidence_count: int | None = None,
    ) -> bool:
        """
        Update pattern confidence and evidence count.

        Returns True if pattern was found and updated.
        """
        table = self.db.open_table("patterns")

        # Get current pattern
        current = self.get_pattern(doc_id)
        if not current:
            return False

        # Build update
        updates = {}
        if confidence is not None:
            updates["confidence"] = confidence
        if evidence_count is not None:
            updates["evidence_count"] = evidence_count

        if updates:
            # LanceDB update via delete + add
            table.delete(f"id = '{doc_id}'")

            record = {
                "id": doc_id,
                "description": current["description"],
                "pattern_type": current["pattern_type"],
                "confidence": float(confidence if confidence is not None else current["confidence"]),
                "evidence_count": int(evidence_count if evidence_count is not None else current["evidence_count"]),
                "vector": get_embedding(current["description"]),
            }
            table.add([record])

        return True

    # =========================================================================
    # Memory operations (for v3 context retrieval)
    # =========================================================================

    def add_memory(self, content: str, memory_type: str) -> str:
        """
        Add a memory for context retrieval.

        Args:
            content: Memory content
            memory_type: Type (decision, learning, problem, etc.)

        Returns:
            Generated memory ID
        """
        from datetime import datetime, timezone

        doc_id = generate_id("mem")

        record = {
            "id": doc_id,
            "content": content,
            "memory_type": memory_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vector": get_embedding(content),
        }

        table = self.db.open_table("memories")
        table.add([record])

        return doc_id

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search memories by text similarity.

        Args:
            query: Search query
            limit: Maximum results
            memory_type: Optional filter by type

        Returns:
            List of matching memories with scores
        """
        table = self.db.open_table("memories")
        query_vector = get_embedding(query)

        search = table.search(query_vector).limit(limit)

        if memory_type:
            search = search.where(f"memory_type = '{memory_type}'", prefilter=True)

        results = search.to_list()

        return [
            {
                "id": r["id"],
                "content": r["content"],
                "type": r["memory_type"],
                "timestamp": r["timestamp"],
                "score": r.get("_distance", 0.0),
            }
            for r in results
        ]

    def memory_exists(self, content: str) -> bool:
        """
        Check if a memory with this content already exists.

        Uses exact match to prevent duplicate seeding.
        """
        table = self.db.open_table("memories")
        # Search for exact content match
        results = table.search().where(
            f"content = '{content.replace(chr(39), chr(39)+chr(39))}'",
            prefilter=True
        ).limit(1).to_list()
        return len(results) > 0

    def memory_count(self) -> int:
        """Get total memory count."""
        table = self.db.open_table("memories")
        return table.count_rows()

    # =========================================================================
    # Stats
    # =========================================================================

    def get_counts(self) -> dict[str, int]:
        """Get count of nodes by type."""
        counts = {}

        for table_name in ["decisions", "entities", "patterns", "memories"]:
            table = self.db.open_table(table_name)
            counts[table_name] = table.count_rows()

        return counts
