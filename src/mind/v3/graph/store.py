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

        # Policies table
        if "policies" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("rule", pa.string()),
                pa.field("scope", pa.string()),
                pa.field("source", pa.string()),
                pa.field("created_at", pa.string()),
                pa.field("active", pa.bool_()),
                pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
            ])
            self.db.create_table("policies", schema=schema)

        # Exceptions table
        if "exceptions" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("policy_id", pa.string()),
                pa.field("condition", pa.string()),
                pa.field("reason", pa.string()),
                pa.field("created_at", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
            ])
            self.db.create_table("exceptions", schema=schema)

        # Precedents table
        if "precedents" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("decision_id", pa.string()),
                pa.field("context", pa.string()),
                pa.field("outcome", pa.string()),
                pa.field("weight", pa.float32()),
                pa.field("created_at", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
            ])
            self.db.create_table("precedents", schema=schema)

        # Outcomes table
        if "outcomes" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("decision_id", pa.string()),
                pa.field("success", pa.bool_()),
                pa.field("feedback", pa.string()),
                pa.field("impact", pa.string()),
                pa.field("created_at", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
            ])
            self.db.create_table("outcomes", schema=schema)

        # Autonomy table
        if "autonomy" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("action_type", pa.string()),
                pa.field("level", pa.string()),
                pa.field("confidence", pa.float32()),
                pa.field("sample_count", pa.int32()),
                pa.field("last_updated", pa.string()),
            ])
            self.db.create_table("autonomy", schema=schema)

    def is_initialized(self) -> bool:
        """Check if store is properly initialized."""
        required = {
            "decisions", "entities", "patterns", "memories",
            "policies", "exceptions", "precedents", "outcomes", "autonomy"
        }
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
    # Policy operations
    # =========================================================================

    def add_policy(self, policy: dict[str, Any]) -> str:
        """
        Add a policy to the graph.

        Args:
            policy: Policy data with rule, scope, source, etc.

        Returns:
            Generated policy ID
        """
        doc_id = generate_id("pol")

        rule = policy.get("rule", "")
        scope = policy.get("scope", "project")
        source = policy.get("source", "inferred")

        record = {
            "id": doc_id,
            "rule": rule,
            "scope": scope,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": policy.get("active", True),
            "vector": get_embedding(rule),
        }

        table = self.db.open_table("policies")
        table.add([record])

        return doc_id

    def get_policy(self, doc_id: str) -> dict[str, Any] | None:
        """Get a policy by ID."""
        table = self.db.open_table("policies")
        results = table.search().where(f"id = '{doc_id}'", prefilter=True).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "rule": row["rule"],
                "scope": row["scope"],
                "source": row["source"],
                "created_at": row["created_at"],
                "active": row["active"],
            }
        return None

    def search_policies(self, query: str, limit: int = 10, active_only: bool = True) -> list[dict[str, Any]]:
        """
        Search policies by text similarity.

        Args:
            query: Search query
            limit: Maximum results
            active_only: If True, only return active policies

        Returns:
            List of matching policies
        """
        table = self.db.open_table("policies")
        query_vector = get_embedding(query)

        search = table.search(query_vector).limit(limit)

        if active_only:
            search = search.where("active = true", prefilter=True)

        results = search.to_list()

        return [
            {
                "id": r["id"],
                "rule": r["rule"],
                "scope": r["scope"],
                "source": r["source"],
                "created_at": r["created_at"],
                "active": r["active"],
            }
            for r in results
        ]

    def deactivate_policy(self, doc_id: str) -> bool:
        """Deactivate a policy. Returns True if found and deactivated."""
        current = self.get_policy(doc_id)
        if not current:
            return False

        table = self.db.open_table("policies")
        table.delete(f"id = '{doc_id}'")

        record = {
            "id": doc_id,
            "rule": current["rule"],
            "scope": current["scope"],
            "source": current["source"],
            "created_at": current["created_at"],
            "active": False,
            "vector": get_embedding(current["rule"]),
        }
        table.add([record])
        return True

    # =========================================================================
    # Exception operations
    # =========================================================================

    def add_exception(self, exception: dict[str, Any]) -> str:
        """
        Add an exception to the graph.

        Args:
            exception: Exception data with policy_id, condition, reason

        Returns:
            Generated exception ID
        """
        doc_id = generate_id("exc")

        policy_id = exception.get("policy_id", "")
        condition = exception.get("condition", "")
        reason = exception.get("reason", "")

        # Embed condition + reason for semantic search
        embed_text = f"{condition} {reason}"

        record = {
            "id": doc_id,
            "policy_id": policy_id,
            "condition": condition,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "vector": get_embedding(embed_text),
        }

        table = self.db.open_table("exceptions")
        table.add([record])

        return doc_id

    def get_exception(self, doc_id: str) -> dict[str, Any] | None:
        """Get an exception by ID."""
        table = self.db.open_table("exceptions")
        results = table.search().where(f"id = '{doc_id}'", prefilter=True).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "policy_id": row["policy_id"],
                "condition": row["condition"],
                "reason": row["reason"],
                "created_at": row["created_at"],
            }
        return None

    def search_exceptions(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search exceptions by text similarity."""
        table = self.db.open_table("exceptions")
        query_vector = get_embedding(query)

        results = table.search(query_vector).limit(limit).to_list()

        return [
            {
                "id": r["id"],
                "policy_id": r["policy_id"],
                "condition": r["condition"],
                "reason": r["reason"],
                "created_at": r["created_at"],
            }
            for r in results
        ]

    def get_exceptions_for_policy(self, policy_id: str) -> list[dict[str, Any]]:
        """Get all exceptions for a specific policy."""
        table = self.db.open_table("exceptions")
        results = table.search().where(
            f"policy_id = '{policy_id}'", prefilter=True
        ).limit(100).to_list()

        return [
            {
                "id": r["id"],
                "policy_id": r["policy_id"],
                "condition": r["condition"],
                "reason": r["reason"],
                "created_at": r["created_at"],
            }
            for r in results
        ]

    # =========================================================================
    # Precedent operations
    # =========================================================================

    def add_precedent(self, precedent: dict[str, Any]) -> str:
        """
        Add a precedent to the graph.

        Args:
            precedent: Precedent data with decision_id, context, outcome

        Returns:
            Generated precedent ID
        """
        doc_id = generate_id("prc")

        decision_id = precedent.get("decision_id", "")
        context = precedent.get("context", "")
        outcome = precedent.get("outcome", "")
        weight = precedent.get("weight", 1.0)

        # Embed context + outcome for semantic search
        embed_text = f"{context} {outcome}"

        record = {
            "id": doc_id,
            "decision_id": decision_id,
            "context": context,
            "outcome": outcome,
            "weight": float(weight),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "vector": get_embedding(embed_text),
        }

        table = self.db.open_table("precedents")
        table.add([record])

        return doc_id

    def get_precedent(self, doc_id: str) -> dict[str, Any] | None:
        """Get a precedent by ID."""
        table = self.db.open_table("precedents")
        results = table.search().where(f"id = '{doc_id}'", prefilter=True).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "decision_id": row["decision_id"],
                "context": row["context"],
                "outcome": row["outcome"],
                "weight": row["weight"],
                "created_at": row["created_at"],
            }
        return None

    def search_precedents(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search precedents by text similarity."""
        table = self.db.open_table("precedents")
        query_vector = get_embedding(query)

        results = table.search(query_vector).limit(limit).to_list()

        return [
            {
                "id": r["id"],
                "decision_id": r["decision_id"],
                "context": r["context"],
                "outcome": r["outcome"],
                "weight": r["weight"],
                "created_at": r["created_at"],
            }
            for r in results
        ]

    def get_precedents_for_decision(self, decision_id: str) -> list[dict[str, Any]]:
        """Get all precedents for a specific decision."""
        table = self.db.open_table("precedents")
        results = table.search().where(
            f"decision_id = '{decision_id}'", prefilter=True
        ).limit(100).to_list()

        return [
            {
                "id": r["id"],
                "decision_id": r["decision_id"],
                "context": r["context"],
                "outcome": r["outcome"],
                "weight": r["weight"],
                "created_at": r["created_at"],
            }
            for r in results
        ]

    # =========================================================================
    # Outcome operations
    # =========================================================================

    def add_outcome(self, outcome: dict[str, Any]) -> str:
        """
        Add an outcome to the graph.

        Args:
            outcome: Outcome data with decision_id, success, feedback, impact

        Returns:
            Generated outcome ID
        """
        doc_id = generate_id("out")

        decision_id = outcome.get("decision_id", "")
        success = outcome.get("success", True)
        feedback = outcome.get("feedback", "")
        impact = outcome.get("impact", "neutral")

        record = {
            "id": doc_id,
            "decision_id": decision_id,
            "success": success,
            "feedback": feedback,
            "impact": impact,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "vector": get_embedding(feedback) if feedback else get_embedding(f"{impact} outcome"),
        }

        table = self.db.open_table("outcomes")
        table.add([record])

        return doc_id

    def get_outcome(self, doc_id: str) -> dict[str, Any] | None:
        """Get an outcome by ID."""
        table = self.db.open_table("outcomes")
        results = table.search().where(f"id = '{doc_id}'", prefilter=True).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "decision_id": row["decision_id"],
                "success": row["success"],
                "feedback": row["feedback"],
                "impact": row["impact"],
                "created_at": row["created_at"],
            }
        return None

    def search_outcomes(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search outcomes by text similarity."""
        table = self.db.open_table("outcomes")
        query_vector = get_embedding(query)

        results = table.search(query_vector).limit(limit).to_list()

        return [
            {
                "id": r["id"],
                "decision_id": r["decision_id"],
                "success": r["success"],
                "feedback": r["feedback"],
                "impact": r["impact"],
                "created_at": r["created_at"],
            }
            for r in results
        ]

    def get_outcome_for_decision(self, decision_id: str) -> dict[str, Any] | None:
        """Get outcome for a specific decision."""
        table = self.db.open_table("outcomes")
        results = table.search().where(
            f"decision_id = '{decision_id}'", prefilter=True
        ).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "decision_id": row["decision_id"],
                "success": row["success"],
                "feedback": row["feedback"],
                "impact": row["impact"],
                "created_at": row["created_at"],
            }
        return None

    # =========================================================================
    # Autonomy operations
    # =========================================================================

    def add_autonomy(self, autonomy: dict[str, Any]) -> str:
        """
        Add or update autonomy level for an action type.

        Args:
            autonomy: Autonomy data with action_type, level, confidence, sample_count

        Returns:
            Generated autonomy ID
        """
        action_type = autonomy.get("action_type", "")

        # Check if autonomy for this action type already exists
        existing = self.get_autonomy_for_action(action_type)
        if existing:
            # Update existing
            return self.update_autonomy(
                existing["id"],
                level=autonomy.get("level"),
                confidence=autonomy.get("confidence"),
                sample_count=autonomy.get("sample_count"),
            )

        doc_id = generate_id("aut")

        record = {
            "id": doc_id,
            "action_type": action_type,
            "level": autonomy.get("level", "ask"),
            "confidence": float(autonomy.get("confidence", 0.0)),
            "sample_count": int(autonomy.get("sample_count", 0)),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        table = self.db.open_table("autonomy")
        table.add([record])

        return doc_id

    def get_autonomy(self, doc_id: str) -> dict[str, Any] | None:
        """Get autonomy by ID."""
        table = self.db.open_table("autonomy")
        results = table.search().where(f"id = '{doc_id}'", prefilter=True).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "action_type": row["action_type"],
                "level": row["level"],
                "confidence": row["confidence"],
                "sample_count": row["sample_count"],
                "last_updated": row["last_updated"],
            }
        return None

    def get_autonomy_for_action(self, action_type: str) -> dict[str, Any] | None:
        """Get autonomy level for a specific action type."""
        table = self.db.open_table("autonomy")
        results = table.search().where(
            f"action_type = '{action_type}'", prefilter=True
        ).limit(1).to_list()

        if results:
            row = results[0]
            return {
                "id": row["id"],
                "action_type": row["action_type"],
                "level": row["level"],
                "confidence": row["confidence"],
                "sample_count": row["sample_count"],
                "last_updated": row["last_updated"],
            }
        return None

    def update_autonomy(
        self,
        doc_id: str,
        level: str | None = None,
        confidence: float | None = None,
        sample_count: int | None = None,
    ) -> str:
        """
        Update autonomy level.

        Returns the ID if successful.
        """
        current = self.get_autonomy(doc_id)
        if not current:
            return ""

        table = self.db.open_table("autonomy")
        table.delete(f"id = '{doc_id}'")

        record = {
            "id": doc_id,
            "action_type": current["action_type"],
            "level": level if level is not None else current["level"],
            "confidence": float(confidence) if confidence is not None else current["confidence"],
            "sample_count": int(sample_count) if sample_count is not None else current["sample_count"],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        table.add([record])
        return doc_id

    def get_all_autonomy(self) -> list[dict[str, Any]]:
        """Get all autonomy levels."""
        table = self.db.open_table("autonomy")
        results = table.search().limit(100).to_list()

        return [
            {
                "id": r["id"],
                "action_type": r["action_type"],
                "level": r["level"],
                "confidence": r["confidence"],
                "sample_count": r["sample_count"],
                "last_updated": r["last_updated"],
            }
            for r in results
        ]

    # =========================================================================
    # Stats
    # =========================================================================

    # Tables that are actively populated by migration and extractors
    ACTIVE_TABLES = {"memories", "decisions", "entities", "patterns"}

    # Tables reserved for future progressive autonomy features
    FUTURE_TABLES = {"policies", "exceptions", "precedents", "outcomes", "autonomy"}

    def get_counts(self) -> dict[str, int]:
        """Get count of nodes by type."""
        counts = {}

        all_tables = list(self.ACTIVE_TABLES | self.FUTURE_TABLES)
        for table_name in all_tables:
            table = self.db.open_table(table_name)
            counts[table_name] = table.count_rows()

        return counts

    def get_table_status(self) -> dict[str, dict[str, Any]]:
        """
        Get status of all tables including whether they're active or future.

        Returns:
            Dict with table name -> {count, status, description}
        """
        status = {}

        table_descriptions = {
            "memories": "Core memory storage for context retrieval",
            "decisions": "Extracted decisions with reasoning",
            "entities": "Files, functions, and concepts mentioned",
            "patterns": "User preferences and habits",
            "policies": "Future: Inferred rules from decisions",
            "exceptions": "Future: Exceptions to policies",
            "precedents": "Future: Historical context for decisions",
            "outcomes": "Future: Decision success tracking",
            "autonomy": "Future: Progressive autonomy levels",
        }

        for table_name in self.ACTIVE_TABLES | self.FUTURE_TABLES:
            table = self.db.open_table(table_name)
            count = table.count_rows()
            is_active = table_name in self.ACTIVE_TABLES

            status[table_name] = {
                "count": count,
                "status": "active" if is_active else "future",
                "description": table_descriptions.get(table_name, ""),
                "populated": count > 0,
            }

        return status

    def get_all_decisions(self) -> list[dict[str, Any]]:
        """Get all decisions (for view generation)."""
        table = self.db.open_table("decisions")
        results = table.search().limit(1000).to_list()

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

    def get_all_patterns(self) -> list[dict[str, Any]]:
        """Get all patterns (for view generation)."""
        table = self.db.open_table("patterns")
        results = table.search().limit(1000).to_list()

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
