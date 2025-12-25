"""
Reranking for Mind v3 retrieval layer.

Refines search results using:
- Cross-encoder models (when available)
- Simple keyword overlap scoring (fallback)
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .search import SearchResult


@dataclass
class RerankerConfig:
    """Configuration for reranker."""

    # Model settings
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    use_gpu: bool = False

    # Reranking settings
    top_k: int = 10
    batch_size: int = 32

    # Fallback settings
    fallback_to_simple: bool = True


class SimpleReranker:
    """
    Simple reranker using keyword overlap.

    Calculates a score based on:
    - Query term frequency in result text
    - Normalized by result length
    """

    def rerank(
        self,
        query: str,
        results: Sequence[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        Rerank results based on keyword overlap.

        Args:
            query: Search query
            results: Results to rerank
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        if not results:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return list(results)[:top_k]

        query_token_set = set(query_tokens)
        scored_results = []

        for result in results:
            text = result.content.get("text", "")
            doc_tokens = self._tokenize(text)

            if not doc_tokens:
                score = 0.0
            else:
                # Count query term occurrences
                doc_token_counts = Counter(doc_tokens)
                overlap = sum(
                    doc_token_counts.get(token, 0)
                    for token in query_tokens
                )

                # Normalize by document length and boost for unique matches
                unique_matches = len(query_token_set & set(doc_tokens))
                score = (overlap / len(doc_tokens)) + (unique_matches * 0.1)

            # Create new result with updated score
            scored_results.append(SearchResult(
                id=result.id,
                content=result.content,
                score=score,
                metadata=result.metadata,
            ))

        # Sort by score descending
        scored_results.sort(key=lambda x: x.score, reverse=True)

        return scored_results[:top_k]

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization."""
        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)
        return [t for t in tokens if len(t) > 1]


class Reranker:
    """
    Reranker with cross-encoder support and fallback.

    Tries to use cross-encoder model, falls back to
    simple keyword-based reranking if unavailable.
    """

    def __init__(self, config: RerankerConfig | None = None):
        """
        Initialize reranker.

        Args:
            config: Reranker configuration
        """
        self.config = config or RerankerConfig()
        self._model = None
        self._fallback = None
        self.is_fallback = False

        self._initialize()

    def _initialize(self) -> None:
        """Initialize the reranking model."""
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self.config.model_name,
                device="cuda" if self.config.use_gpu else "cpu",
            )
            self.is_fallback = False

        except Exception:
            # Fall back to simple reranker
            if self.config.fallback_to_simple:
                self._fallback = SimpleReranker()
                self.is_fallback = True
            else:
                raise

    def rerank(
        self,
        query: str,
        results: Sequence[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """
        Rerank results using cross-encoder or fallback.

        Args:
            query: Search query
            results: Results to rerank
            top_k: Number of results (defaults to config)

        Returns:
            Reranked results
        """
        k = top_k or self.config.top_k

        if not results:
            return []

        if self._model is not None:
            return self._cross_encoder_rerank(query, results, k)
        elif self._fallback is not None:
            return self._fallback.rerank(query, results, k)
        else:
            raise RuntimeError("No reranker available")

    def _cross_encoder_rerank(
        self,
        query: str,
        results: Sequence[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Rerank using cross-encoder model."""
        # Prepare pairs for cross-encoder
        pairs = [
            [query, result.content.get("text", "")]
            for result in results
        ]

        # Get scores
        scores = self._model.predict(
            pairs,
            batch_size=self.config.batch_size,
        )

        # Create results with new scores
        scored_results = [
            SearchResult(
                id=result.id,
                content=result.content,
                score=float(score),
                metadata=result.metadata,
            )
            for result, score in zip(results, scores)
        ]

        # Sort by score descending
        scored_results.sort(key=lambda x: x.score, reverse=True)

        return scored_results[:top_k]
