"""Mind v3 context retrieval layer.

Hybrid search combining:
- Dense vectors (semantic similarity)
- Sparse BM25 (keyword matching)
- Reranking (cross-encoder scoring)
- Context injection via UserPromptSubmit hook
"""
from .embeddings import EmbeddingService, EmbeddingConfig, HashEmbedding
from .search import HybridSearch, SearchConfig, SearchResult, SearchMode
from .reranker import Reranker, RerankerConfig, SimpleReranker
from .context_injection import ContextInjector, ContextInjectorConfig, InjectedContext

__all__ = [
    "EmbeddingService",
    "EmbeddingConfig",
    "HashEmbedding",
    "HybridSearch",
    "SearchConfig",
    "SearchResult",
    "SearchMode",
    "Reranker",
    "RerankerConfig",
    "SimpleReranker",
    "ContextInjector",
    "ContextInjectorConfig",
    "InjectedContext",
]
