"""Semantic similarity for loop detection and search.

Uses sentence-transformers for embedding-based similarity.
"""

from typing import Optional, Any

# Lazy-loaded model (expensive to load, so do it only when needed)
_model = None
_model_load_attempted = False


def _get_model():
    """Lazy-load the sentence-transformer model."""
    global _model, _model_load_attempted

    if _model_load_attempted:
        return _model

    _model_load_attempted = True

    from sentence_transformers import SentenceTransformer
    # all-MiniLM-L6-v2 is small (~80MB), fast, and good for short text similarity
    _model = SentenceTransformer('all-MiniLM-L6-v2')

    return _model


def cosine_similarity(a, b) -> float:
    """Calculate cosine similarity between two vectors."""
    import numpy as np
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts.

    Uses sentence-transformers embeddings.

    Returns:
        Similarity score between 0.0 and 1.0
    """
    model = _get_model()
    embeddings = model.encode([text1, text2])
    return cosine_similarity(embeddings[0], embeddings[1])


def find_similar_rejection(
    new_message: str,
    existing_rejections: list[str],
    threshold: float = 0.6,
) -> Optional[dict]:
    """Find if new message is semantically similar to any existing rejection.

    Args:
        new_message: The new rejection to check
        existing_rejections: List of existing rejections from SESSION.md
        threshold: Similarity threshold (0.6 = 60% similar)

    Returns:
        Dict with similar_to, similarity, suggestion if match found, else None
    """
    if not new_message or not existing_rejections:
        return None

    best_match = None
    best_similarity = 0.0

    for existing in existing_rejections:
        if not existing:
            continue

        similarity = semantic_similarity(new_message, existing)

        if similarity >= threshold and similarity > best_similarity:
            best_similarity = similarity
            best_match = existing

    if best_match:
        return {
            "similar_to": best_match,
            "similarity": round(best_similarity, 2),
            "suggestion": "You may be looping. Call mind_session() to review all attempts before trying again."
        }

    return None


def semantic_search(
    query: str,
    items: list[dict[str, Any]],
    content_key: str = "content",
    threshold: float = 0.3,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Semantic search across a list of items.

    Args:
        query: The search query
        items: List of dicts containing content to search
        content_key: Key in dict containing text to match against
        threshold: Minimum similarity score to include (0.0-1.0)
        limit: Maximum results to return

    Returns:
        List of items with similarity scores, sorted by relevance
    """
    if not query or not items:
        return []

    model = _get_model()
    if model is None:
        return []

    # Get query embedding
    query_embedding = model.encode(query)

    # Get embeddings for all items
    contents = [item.get(content_key, "") for item in items]
    content_embeddings = model.encode(contents)

    # Calculate similarities and attach to items
    results = []
    for i, item in enumerate(items):
        similarity = cosine_similarity(query_embedding, content_embeddings[i])
        if similarity >= threshold:
            result = item.copy()
            result["semantic_similarity"] = round(similarity, 3)
            results.append(result)

    # Sort by similarity descending
    results.sort(key=lambda x: x["semantic_similarity"], reverse=True)
    return results[:limit]


def semantic_search_strings(
    query: str,
    strings: list[str],
    threshold: float = 0.3,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Semantic search across a list of strings.

    Args:
        query: The search query
        strings: List of strings to search
        threshold: Minimum similarity score to include (0.0-1.0)
        limit: Maximum results to return

    Returns:
        List of dicts with content and similarity scores
    """
    if not query or not strings:
        return []

    model = _get_model()
    if model is None:
        return []

    # Get query embedding
    query_embedding = model.encode(query)

    # Get embeddings for all strings
    string_embeddings = model.encode(strings)

    # Calculate similarities
    results = []
    for i, s in enumerate(strings):
        if not s.strip():
            continue
        similarity = cosine_similarity(query_embedding, string_embeddings[i])
        if similarity >= threshold:
            results.append({
                "content": s,
                "line_index": i,
                "semantic_similarity": round(similarity, 3),
            })

    # Sort by similarity descending
    results.sort(key=lambda x: x["semantic_similarity"], reverse=True)
    return results[:limit]
