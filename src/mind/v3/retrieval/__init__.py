"""Mind v3 context retrieval layer.

Hybrid search combining:
- Dense vectors (semantic similarity)
- Sparse BM25 (keyword matching)
- Reranking (cross-encoder scoring)
- Context injection via UserPromptSubmit hook
"""
