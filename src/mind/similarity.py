"""Semantic similarity for loop detection.

Uses sentence-transformers for embedding-based similarity with fallback to keyword matching.
"""

import re
from typing import Optional

# Lazy-loaded model (expensive to load, so do it only when needed)
_model = None
_model_load_attempted = False


def _get_model():
    """Lazy-load the sentence-transformer model."""
    global _model, _model_load_attempted

    if _model_load_attempted:
        return _model

    _model_load_attempted = True

    try:
        from sentence_transformers import SentenceTransformer
        # all-MiniLM-L6-v2 is small (~80MB), fast, and good for short text similarity
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    except ImportError:
        # sentence-transformers not installed, will fall back to keyword matching
        _model = None
    except Exception:
        # Model download failed or other issue
        _model = None

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


# Stop words for keyword fallback
STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "not", "but",
    "are", "was", "been", "will", "would", "could", "should", "can", "may",
    "into", "then", "than", "also", "just", "more", "some", "such", "when",
    "try", "tried", "trying", "again", "maybe", "perhaps", "let", "lets",
}


def extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text (3+ chars, skip stop words)."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return {w for w in words if w not in STOP_WORDS}


def keyword_similarity(text1: str, text2: str) -> float:
    """Calculate keyword overlap similarity (fallback method)."""
    kw1 = extract_keywords(text1)
    kw2 = extract_keywords(text2)

    if not kw1 or not kw2:
        return 0.0

    overlap = len(kw1 & kw2)
    return overlap / min(len(kw1), len(kw2))


def semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts.

    Uses sentence-transformers embeddings if available, falls back to keyword overlap.

    Returns:
        Similarity score between 0.0 and 1.0
    """
    model = _get_model()

    if model is None:
        # Fallback to keyword matching
        return keyword_similarity(text1, text2)

    try:
        # Encode both texts
        embeddings = model.encode([text1, text2])
        return cosine_similarity(embeddings[0], embeddings[1])
    except Exception:
        # If encoding fails, fall back to keyword matching
        return keyword_similarity(text1, text2)


def find_similar_rejection(
    new_message: str,
    existing_rejections: list[str],
    threshold: float = 0.7,
) -> Optional[dict]:
    """Find if new message is semantically similar to any existing rejection.

    Args:
        new_message: The new rejection to check
        existing_rejections: List of existing rejections from SESSION.md
        threshold: Similarity threshold (0.7 = 70% similar, mem0's default)

    Returns:
        Dict with similar_to, similarity, method, suggestion if match found, else None
    """
    if not new_message or not existing_rejections:
        return None

    model = _get_model()
    method = "semantic" if model else "keyword"

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
            "method": method,
            "suggestion": "You may be looping. Call mind_session() to review all attempts before trying again."
        }

    return None


def is_semantic_available() -> bool:
    """Check if semantic similarity (sentence-transformers) is available."""
    return _get_model() is not None
