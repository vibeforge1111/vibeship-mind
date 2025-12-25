"""
UserPromptSubmit hook for Claude Code integration.

Injects relevant context before Claude sees the user's prompt.
Uses v3 retrieval and memory systems for intelligent context selection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PromptSubmitConfig:
    """Configuration for prompt submit hook."""

    enabled: bool = True
    max_context_items: int = 5
    min_relevance_score: float = 0.3


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
    ):
        """
        Initialize hook.

        Args:
            project_path: Path to project directory
            config: Hook configuration
        """
        self.project_path = project_path
        self.config = config or PromptSubmitConfig()

        # In-memory storage for this session
        self._memories: list[dict[str, Any]] = []
        self._retrieval_count: int = 0

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
        self._memories.append({
            "content": content,
            "type": memory_type,
        })

    def get_retrieval_stats(self) -> dict:
        """
        Get statistics about retrievals.

        Returns:
            Dictionary with retrieval stats
        """
        return {
            "total_retrievals": self._retrieval_count,
            "memory_count": len(self._memories),
        }

    def _search_memories(self, query: str) -> list[dict]:
        """
        Search memories for relevant items.

        Uses simple keyword matching for now.
        Will integrate with v3 retrieval system.

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

            # Simple relevance: word overlap
            overlap = query_words & content_words
            if overlap:
                score = len(overlap) / max(len(query_words), 1)
                if score >= self.config.min_relevance_score:
                    relevant.append({
                        **memory,
                        "score": score,
                    })

        # Sort by score and limit
        relevant.sort(key=lambda x: x["score"], reverse=True)
        return relevant[: self.config.max_context_items]

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
