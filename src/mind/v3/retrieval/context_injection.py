"""
Context injection for Mind v3 retrieval layer.

Formats search results into context that can be injected
into Claude's prompt via the UserPromptSubmit hook.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from .search import HybridSearch, SearchResult, SearchMode
from .reranker import Reranker, RerankerConfig


@dataclass
class ContextInjectorConfig:
    """Configuration for context injection."""

    # Result limits
    max_context_items: int = 5
    max_context_length: int = 2000  # Characters
    min_relevance_score: float = 0.0  # RRF scores are typically 0.001-0.02

    # Reranking
    use_reranking: bool = False

    # Formatting
    include_scores: bool = False
    group_by_type: bool = False


@dataclass
class InjectedContext:
    """Context to inject into user prompt."""

    items: list[dict[str, Any]]
    total_items: int
    truncated: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """
        Format context as markdown for injection.

        Returns:
            Markdown-formatted context string
        """
        if not self.items:
            return ""

        lines = ["# Relevant Context", ""]

        # Check if we should group by type
        include_scores = self.metadata.get("include_scores", False)
        group_by_type = self.metadata.get("group_by_type", False)

        if group_by_type:
            # Group items by type
            grouped: dict[str, list[dict]] = {}
            for item in self.items:
                item_type = item.get("type", "other")
                if item_type not in grouped:
                    grouped[item_type] = []
                grouped[item_type].append(item)

            # Format each group
            for type_name, type_items in grouped.items():
                lines.append(f"## {type_name.title()}")
                lines.append("")
                for item in type_items:
                    lines.append(self._format_item(item, include_scores))
                lines.append("")
        else:
            # Simple list format
            for item in self.items:
                lines.append(self._format_item(item, include_scores))

        if self.truncated:
            lines.append("")
            lines.append(f"*({self.total_items - len(self.items)} more items truncated)*")

        return "\n".join(lines)

    def _format_item(self, item: dict, include_scores: bool) -> str:
        """Format a single item."""
        text = item.get("text", "")
        score = item.get("score", 0)

        if include_scores:
            relevance_pct = int(score * 100) if score <= 1 else score
            return f"- {text} (relevance: {relevance_pct}%)"
        else:
            return f"- {text}"


class ContextInjector:
    """
    Injects relevant context into user prompts.

    Uses hybrid search (and optional reranking) to find
    relevant memories and format them for injection.
    """

    def __init__(
        self,
        search: HybridSearch,
        config: ContextInjectorConfig | None = None,
        reranker: Reranker | None = None,
    ):
        """
        Initialize context injector.

        Args:
            search: Hybrid search instance with indexed documents
            config: Injection configuration
            reranker: Optional reranker (created if use_reranking=True)
        """
        self.search = search
        self.config = config or ContextInjectorConfig()
        self._reranker = reranker

        # Create reranker if needed
        if self.config.use_reranking and self._reranker is None:
            self._reranker = Reranker(
                RerankerConfig(fallback_to_simple=True)
            )

    def inject(self, query: str) -> InjectedContext:
        """
        Find and format relevant context for a query.

        Args:
            query: User's query/prompt

        Returns:
            InjectedContext with formatted results
        """
        if not query.strip():
            return InjectedContext(
                items=[],
                total_items=0,
                truncated=False,
            )

        # Search for relevant documents
        results = self.search.search(
            query,
            mode=SearchMode.HYBRID,
            top_k=self.config.max_context_items * 2,  # Get more for filtering
        )

        # Apply reranking if enabled
        if self._reranker is not None and results:
            results = self._reranker.rerank(
                query,
                results,
                top_k=self.config.max_context_items * 2,
            )

        # Filter by minimum score
        results = [
            r for r in results
            if r.score >= self.config.min_relevance_score
        ]

        # Convert to items
        items = self._results_to_items(results)

        # Truncate if needed
        items, truncated = self._truncate_items(items)

        return InjectedContext(
            items=items,
            total_items=len(results),
            truncated=truncated,
            metadata={
                "include_scores": self.config.include_scores,
                "group_by_type": self.config.group_by_type,
            },
        )

    def _results_to_items(self, results: Sequence[SearchResult]) -> list[dict]:
        """Convert search results to item dicts."""
        items = []
        for result in results:
            item = {
                "id": result.id,
                "text": result.content.get("text", ""),
                "score": result.score,
            }

            # Include metadata type if present
            if "type" in result.metadata:
                item["type"] = result.metadata["type"]

            items.append(item)

        return items

    def _truncate_items(
        self,
        items: list[dict],
    ) -> tuple[list[dict], bool]:
        """
        Truncate items to fit within limits.

        Returns:
            (truncated_items, was_truncated)
        """
        # Limit by count first
        if len(items) > self.config.max_context_items:
            items = items[:self.config.max_context_items]
            truncated = True
        else:
            truncated = False

        # Limit by total length
        total_length = 0
        kept_items = []

        for item in items:
            text_len = len(item.get("text", ""))
            if total_length + text_len > self.config.max_context_length:
                truncated = True
                break
            kept_items.append(item)
            total_length += text_len

        return kept_items, truncated
