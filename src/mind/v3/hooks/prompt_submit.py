"""
UserPromptSubmit hook for Claude Code integration.

Injects relevant context before Claude sees the user's prompt.
Uses v3 retrieval and memory systems for intelligent context selection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

from ..memory.decay import DecayManager, DecayConfig
from ..memory.working_memory import WorkingMemory, MemoryItem, MemoryType
from ..intelligence.extractors.entity import LocalEntityExtractor
from ..intelligence.extractors.decision import LocalDecisionExtractor
from ..retrieval.query_expander import QueryExpander, ExpanderConfig

if TYPE_CHECKING:
    from ..graph.store import GraphStore


@dataclass
class PromptSubmitConfig:
    """Configuration for prompt submit hook."""

    enabled: bool = True
    max_context_items: int = 5
    min_relevance_score: float = 0.3
    use_query_expansion: bool = True
    max_expanded_searches: int = 2  # Max additional searches from expansion


@dataclass
class HookResult:
    """Result from hook processing."""

    success: bool
    context_injected: str
    items_count: int
    metadata: dict = field(default_factory=dict)


class PromptSubmitHook:
    """
    Hook that runs when user submits a prompt.

    Retrieves relevant context from memory and injects it
    before Claude processes the prompt.
    """

    def __init__(
        self,
        project_path: Path,
        config: PromptSubmitConfig | None = None,
        graph_store: "GraphStore | None" = None,
    ):
        """
        Initialize hook.

        Args:
            project_path: Path to project directory
            config: Hook configuration
            graph_store: Optional GraphStore for persistent memory
        """
        self.project_path = project_path
        self.config = config or PromptSubmitConfig()

        # Use GraphStore for persistence, fall back to in-memory
        self._graph_store = graph_store
        self._memories: list[dict[str, Any]] = []  # Fallback if no store
        self._retrieval_count: int = 0

        # Decay manager for time-based activation decay
        self._decay_manager = DecayManager(DecayConfig(half_life_hours=48))

        # Working memory for session tracking
        self._working_memory = WorkingMemory()

        # Entity extractor for extracting entities from memories
        self._entity_extractor = LocalEntityExtractor()

        # Decision extractor for extracting structured decisions
        self._decision_extractor = LocalDecisionExtractor()

        # Query expander for better retrieval
        self._query_expander = QueryExpander(ExpanderConfig(
            enabled=self.config.use_query_expansion,
            max_expansions=self.config.max_expanded_searches,
        ))

    def process(self, query: str) -> HookResult:
        """
        Process user query and return relevant context.

        Args:
            query: User's prompt text

        Returns:
            HookResult with context to inject
        """
        # If disabled, return empty result
        if not self.config.enabled:
            return HookResult(
                success=True,
                context_injected="",
                items_count=0,
            )

        # Empty query, no context needed
        if not query.strip():
            return HookResult(
                success=True,
                context_injected="",
                items_count=0,
            )

        # Search for relevant memories
        relevant = self._search_memories(query)

        # Format context
        if relevant:
            context = self._format_context(relevant)
            self._retrieval_count += 1
        else:
            context = ""

        return HookResult(
            success=True,
            context_injected=context,
            items_count=len(relevant),
        )

    def add_to_memory(
        self,
        content: str,
        memory_type: str,
    ) -> None:
        """
        Add content to memory for later retrieval.

        Args:
            content: Memory content
            memory_type: Type of memory (decision, learning, pattern, etc.)
        """
        if self._graph_store:
            # Use persistent storage
            self._graph_store.add_memory(content, memory_type)

            # Extract entities from content
            try:
                entity_extraction = self._entity_extractor.extract(content)
                if entity_extraction.content.get("entities"):
                    for ent in entity_extraction.content["entities"]:
                        self._graph_store.add_entity({
                            "name": ent["name"],
                            "type": ent["type"],
                            "description": ent.get("description") or content[:100],
                        })
            except Exception:
                pass  # Don't fail if extraction fails

            # Extract structured decisions when memory_type is decision
            if memory_type == "decision":
                try:
                    decision_extraction = self._decision_extractor.extract(content)
                    if decision_extraction.confidence > 0.5:
                        self._graph_store.add_decision({
                            "action": decision_extraction.content.get("action", content),
                            "reasoning": decision_extraction.content.get("reasoning", ""),
                            "alternatives": decision_extraction.content.get("alternatives", []),
                            "confidence": decision_extraction.confidence,
                        })
                except Exception:
                    pass  # Don't fail if extraction fails
        else:
            # Fall back to in-memory
            self._memories.append({
                "content": content,
                "type": memory_type,
            })

        # Add to working memory for session tracking
        mem_type = MemoryType.DECISION if memory_type == "decision" else MemoryType.LEARNING
        if memory_type == "problem":
            mem_type = MemoryType.EVENT
        item = MemoryItem(
            id=f"wm_{len(self._working_memory._items)}",
            content=content,
            memory_type=mem_type,
            activation=1.0,
            importance=0.5,
        )
        self._working_memory.add(item)

    def get_retrieval_stats(self) -> dict:
        """
        Get statistics about retrievals.

        Returns:
            Dictionary with retrieval stats
        """
        if self._graph_store:
            memory_count = self._graph_store.memory_count()
        else:
            memory_count = len(self._memories)

        return {
            "total_retrievals": self._retrieval_count,
            "memory_count": memory_count,
        }

    def _search_memories(self, query: str) -> list[dict]:
        """
        Search memories for relevant items.

        Uses query expansion and GraphStore vector search when available,
        falls back to keyword matching otherwise.

        Args:
            query: Search query

        Returns:
            List of relevant memories
        """
        # Expand the query for better retrieval
        expanded = self._query_expander.expand(query)

        if self._graph_store:
            return self._search_with_expansion(query, expanded)

        # Fall back to keyword matching (no expansion for in-memory)
        return self._search_in_memory(query)

    def _search_with_expansion(self, query: str, expanded) -> list[dict]:
        """
        Search with query expansion using GraphStore.

        Args:
            query: Original query
            expanded: ExpandedQuery with sub-queries and entities

        Returns:
            Deduplicated and ranked results
        """
        all_results: list[dict] = []
        seen_ids: set[str] = set()

        # Search with original query (highest priority)
        primary_results = self._graph_store.search_memories(
            query,
            limit=self.config.max_context_items,
        )
        for r in primary_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                r["_source"] = "primary"
                all_results.append(r)

        # Search with sub-queries if enabled
        if self.config.use_query_expansion:
            for sub_query in expanded.sub_queries[:self.config.max_expanded_searches]:
                sub_results = self._graph_store.search_memories(
                    sub_query,
                    limit=2,  # Fewer results per sub-query
                )
                for r in sub_results:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        r["_source"] = "sub_query"
                        all_results.append(r)

            # Search for extracted entities
            for entity in expanded.entities[:2]:
                entity_results = self._graph_store.search_entities(entity, limit=2)
                for ent in entity_results:
                    # Convert entity to memory-like format for consistent handling
                    mem_id = f"ent_{ent['id']}"
                    if mem_id not in seen_ids:
                        seen_ids.add(mem_id)
                        all_results.append({
                            "id": mem_id,
                            "content": f"{ent['name']}: {ent.get('description', '')}",
                            "type": "entity",
                            "score": 0.0,  # Will be recalculated
                            "_source": "entity",
                        })

        # Convert distances to scores and filter
        scored_results = self._score_and_rank(all_results, query, expanded)

        return scored_results[:self.config.max_context_items]

    def _score_and_rank(self, results: list[dict], query: str, expanded) -> list[dict]:
        """
        Score and rank results considering source and relevance.

        Args:
            results: Raw results from searches
            query: Original query
            expanded: ExpandedQuery for keyword matching

        Returns:
            Scored and sorted results
        """
        keywords = expanded.get_keywords()
        query_lower = query.lower()

        scored = []
        for r in results:
            # Start with distance-based score
            distance = r.get("score", 0.0)
            # Convert L2 distance to similarity (0-1 range)
            base_score = max(0.0, 1.0 - (distance / 2.0))

            # Boost for primary results
            if r.get("_source") == "primary":
                base_score += 0.1

            # Boost for keyword matches in content
            content_lower = r.get("content", "").lower()
            matching_keywords = sum(1 for kw in keywords if kw in content_lower)
            keyword_boost = min(matching_keywords * 0.05, 0.2)
            base_score += keyword_boost

            # Boost for exact query substring match
            if query_lower in content_lower:
                base_score += 0.15

            r["score"] = min(base_score, 1.0)  # Cap at 1.0
            scored.append(r)

        # Filter by minimum score and sort
        filtered = [r for r in scored if r["score"] >= self.config.min_relevance_score]
        filtered.sort(key=lambda x: x["score"], reverse=True)

        return filtered

    def _search_in_memory(self, query: str) -> list[dict]:
        """
        Fallback keyword-based search for in-memory storage.

        Args:
            query: Search query

        Returns:
            List of relevant memories
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        relevant = []
        for memory in self._memories:
            content_lower = memory["content"].lower()
            content_words = set(content_lower.split())

            # Relevance: word overlap scored by the smaller set
            overlap = query_words & content_words
            if overlap:
                min_size = min(len(query_words), len(content_words))
                score = len(overlap) / max(min_size, 1)
                if score >= self.config.min_relevance_score:
                    relevant.append({
                        **memory,
                        "score": score,
                    })

        # Sort by score and limit
        relevant.sort(key=lambda x: x["score"], reverse=True)
        return relevant[:self.config.max_context_items]

    def _format_context(self, memories: list[dict]) -> str:
        """
        Format memories as markdown context.

        Args:
            memories: List of relevant memories

        Returns:
            Markdown formatted context
        """
        if not memories:
            return ""

        lines = ["## Relevant Context"]
        for memory in memories:
            mem_type = memory.get("type", "memory")
            content = memory["content"]
            lines.append(f"- [{mem_type}] {content}")

        return "\n".join(lines)
