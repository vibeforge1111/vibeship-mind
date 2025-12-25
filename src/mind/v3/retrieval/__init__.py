"""Mind v3 context retrieval layer.

Hybrid search combining:
- Dense vectors (semantic similarity)
- Sparse BM25 (keyword matching)
- Reranking (cross-encoder scoring)
- Context injection via UserPromptSubmit hook
"""
from .embeddings import EmbeddingService, EmbeddingConfig, HashEmbedding
from .search import HybridSearch, SearchConfig, SearchResult, SearchMode

__all__ = [
    "EmbeddingService",
    "EmbeddingConfig",
    "HashEmbedding",
    "HybridSearch",
    "SearchConfig",
    "SearchResult",
    "SearchMode",
]
