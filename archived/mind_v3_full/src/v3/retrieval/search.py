"""
Hybrid search for Mind v3 retrieval layer.

Combines vector search (semantic similarity) with keyword search (BM25)
using Reciprocal Rank Fusion (RRF) to merge results.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

import numpy as np

from .embeddings import EmbeddingService, EmbeddingConfig


class SearchMode(str, Enum):
    """Search mode options."""

    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"


@dataclass
class SearchConfig:
    """Configuration for hybrid search."""

    mode: SearchMode = SearchMode.HYBRID
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    top_k: int = 10

    # BM25 parameters
    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    # RRF parameter
    rrf_k: int = 60


@dataclass
class SearchResult:
    """A single search result."""

    id: str
    content: dict[str, Any]
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Internal document representation."""

    id: str
    text: str
    embedding: list[float]
    tokens: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridSearch:
    """
    Hybrid search combining vector and keyword search.

    Uses:
    - Dense vectors for semantic similarity
    - BM25 for keyword matching
    - RRF for result fusion
    """

    def __init__(
        self,
        config: SearchConfig | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        """
        Initialize hybrid search.

        Args:
            config: Search configuration
            embedding_service: Optional embedding service (creates default if not provided)
        """
        self.config = config or SearchConfig()
        self.embedding_service = embedding_service or EmbeddingService(
            EmbeddingConfig(fallback_to_hash=True)
        )

        self._documents: dict[str, Document] = {}
        self._avg_doc_length: float = 0.0
        self._doc_freqs: Counter[str] = Counter()

    @property
    def document_count(self) -> int:
        """Get number of documents."""
        return len(self._documents)

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a single document.

        Args:
            doc_id: Document ID
            text: Document text
            metadata: Optional metadata
        """
        tokens = self._tokenize(text)
        embedding = self.embedding_service.embed(text)

        self._documents[doc_id] = Document(
            id=doc_id,
            text=text,
            embedding=embedding,
            tokens=tokens,
            metadata=metadata or {},
        )

        # Update document frequencies
        unique_tokens = set(tokens)
        for token in unique_tokens:
            self._doc_freqs[token] += 1

        # Update average document length
        self._update_avg_doc_length()

    def add_documents(self, documents: Sequence[dict[str, Any]]) -> None:
        """
        Add multiple documents.

        Args:
            documents: List of documents with 'id', 'text', and optional 'metadata'
        """
        for doc in documents:
            self.add_document(
                doc_id=doc.get("id", ""),
                text=doc.get("text", ""),
                metadata=doc.get("metadata"),
            )

    def remove_document(self, doc_id: str) -> bool:
        """
        Remove a document.

        Args:
            doc_id: Document ID to remove

        Returns:
            True if document was removed
        """
        if doc_id not in self._documents:
            return False

        doc = self._documents[doc_id]

        # Update document frequencies
        unique_tokens = set(doc.tokens)
        for token in unique_tokens:
            self._doc_freqs[token] -= 1
            if self._doc_freqs[token] <= 0:
                del self._doc_freqs[token]

        del self._documents[doc_id]
        self._update_avg_doc_length()

        return True

    def clear(self) -> None:
        """Remove all documents."""
        self._documents.clear()
        self._doc_freqs.clear()
        self._avg_doc_length = 0.0

    def search(
        self,
        query: str,
        mode: SearchMode | None = None,
        config: SearchConfig | None = None,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """
        Search documents.

        Args:
            query: Search query
            mode: Search mode (overrides config)
            config: Search config (overrides instance config)
            top_k: Number of results (overrides config)

        Returns:
            List of search results sorted by score
        """
        cfg = config or self.config
        search_mode = mode or cfg.mode
        k = top_k or cfg.top_k

        if not self._documents:
            return []

        if not query.strip():
            # Return top documents by some default scoring
            return self._get_top_documents(k)

        if search_mode == SearchMode.VECTOR_ONLY:
            return self._vector_search(query, k)
        elif search_mode == SearchMode.KEYWORD_ONLY:
            return self._keyword_search(query, k)
        else:
            return self._hybrid_search(query, cfg, k)

    def _vector_search(self, query: str, top_k: int) -> list[SearchResult]:
        """Perform vector-only search."""
        query_embedding = self.embedding_service.embed(query)

        scores = []
        for doc_id, doc in self._documents.items():
            score = self.embedding_service.similarity(
                query_embedding, doc.embedding
            )
            scores.append((doc_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return [
            SearchResult(
                id=doc_id,
                content={"text": self._documents[doc_id].text},
                score=score,
                metadata=self._documents[doc_id].metadata,
            )
            for doc_id, score in scores[:top_k]
        ]

    def _keyword_search(self, query: str, top_k: int) -> list[SearchResult]:
        """Perform BM25 keyword search."""
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        scores = []
        n_docs = len(self._documents)

        for doc_id, doc in self._documents.items():
            score = self._bm25_score(query_tokens, doc, n_docs)
            scores.append((doc_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return [
            SearchResult(
                id=doc_id,
                content={"text": self._documents[doc_id].text},
                score=score,
                metadata=self._documents[doc_id].metadata,
            )
            for doc_id, score in scores[:top_k]
            if score > 0
        ]

    def _hybrid_search(
        self,
        query: str,
        config: SearchConfig,
        top_k: int,
    ) -> list[SearchResult]:
        """Perform hybrid search with RRF fusion."""
        # Get more results than needed for fusion
        fetch_k = min(top_k * 3, len(self._documents))

        vector_results = self._vector_search(query, fetch_k)
        keyword_results = self._keyword_search(query, fetch_k)

        # Reciprocal Rank Fusion
        rrf_scores: dict[str, float] = {}
        k = config.rrf_k

        # Add vector scores
        for rank, result in enumerate(vector_results):
            rrf_score = config.vector_weight / (k + rank + 1)
            rrf_scores[result.id] = rrf_scores.get(result.id, 0) + rrf_score

        # Add keyword scores
        for rank, result in enumerate(keyword_results):
            rrf_score = config.keyword_weight / (k + rank + 1)
            rrf_scores[result.id] = rrf_scores.get(result.id, 0) + rrf_score

        # Sort by RRF score
        sorted_ids = sorted(
            rrf_scores.keys(),
            key=lambda x: rrf_scores[x],
            reverse=True,
        )

        return [
            SearchResult(
                id=doc_id,
                content={"text": self._documents[doc_id].text},
                score=rrf_scores[doc_id],
                metadata=self._documents[doc_id].metadata,
            )
            for doc_id in sorted_ids[:top_k]
        ]

    def _bm25_score(
        self,
        query_tokens: list[str],
        doc: Document,
        n_docs: int,
    ) -> float:
        """Calculate BM25 score for a document."""
        k1 = self.config.bm25_k1
        b = self.config.bm25_b
        avg_dl = self._avg_doc_length or 1.0

        score = 0.0
        doc_len = len(doc.tokens)
        doc_token_counts = Counter(doc.tokens)

        for token in query_tokens:
            if token not in doc_token_counts:
                continue

            # Document frequency
            df = self._doc_freqs.get(token, 0)
            if df == 0:
                continue

            # IDF
            idf = np.log((n_docs - df + 0.5) / (df + 0.5) + 1)

            # Term frequency in document
            tf = doc_token_counts[token]

            # BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_len / avg_dl))
            score += idf * (numerator / denominator)

        return score

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization."""
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)
        # Filter short tokens
        return [t for t in tokens if len(t) > 1]

    def _update_avg_doc_length(self) -> None:
        """Update average document length."""
        if not self._documents:
            self._avg_doc_length = 0.0
            return

        total_length = sum(len(doc.tokens) for doc in self._documents.values())
        self._avg_doc_length = total_length / len(self._documents)

    def _get_top_documents(self, top_k: int) -> list[SearchResult]:
        """Get top documents when no query provided."""
        results = []
        for doc_id, doc in list(self._documents.items())[:top_k]:
            results.append(SearchResult(
                id=doc_id,
                content={"text": doc.text},
                score=1.0,
                metadata=doc.metadata,
            ))
        return results
