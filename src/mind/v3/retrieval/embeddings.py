"""
Embedding service for Mind v3 retrieval layer.

Provides text embeddings using:
- sentence-transformers (preferred, when available)
- Hash-based fallback (deterministic, for testing/offline)

The default model is all-MiniLM-L6-v2 (384 dimensions),
which provides a good balance of speed and quality.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass
class EmbeddingConfig:
    """Configuration for embedding service."""

    # Model settings
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    use_gpu: bool = False

    # Processing settings
    normalize: bool = True
    batch_size: int = 32

    # Fallback settings
    fallback_to_hash: bool = True


class HashEmbedding:
    """
    Deterministic hash-based embedding fallback.

    Uses SHA-384 to create reproducible embeddings.
    Useful for testing and when ML models aren't available.
    """

    def __init__(self, dimension: int = 384, normalize: bool = True):
        """Initialize hash embedding."""
        self.dimension = dimension
        self.normalize = normalize

    def embed(self, text: str) -> list[float]:
        """
        Create embedding from text using hash.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Use SHA-384 for deterministic hashing
        hash_bytes = hashlib.sha384(text.encode("utf-8")).digest()

        # Convert to floats in range [-1, 1]
        embedding = []
        for i in range(self.dimension):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val / 127.5) - 1.0)

        if self.normalize:
            embedding = self._normalize(embedding)

        return embedding

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple texts."""
        return [self.embed(text) for text in texts]

    def _normalize(self, embedding: list[float]) -> list[float]:
        """Normalize embedding to unit length."""
        arr = np.array(embedding)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()


class EmbeddingService:
    """
    Main embedding service with model loading and fallback.

    Tries to load sentence-transformers model, falls back to
    hash-based embeddings if unavailable.
    """

    def __init__(self, config: EmbeddingConfig | None = None):
        """
        Initialize embedding service.

        Args:
            config: Embedding configuration
        """
        self.config = config or EmbeddingConfig()
        self.dimension = self.config.dimension
        self._model = None
        self._fallback = None
        self.is_fallback = False

        self._initialize()

    def _initialize(self) -> None:
        """Initialize the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.config.model_name,
                device="cuda" if self.config.use_gpu else "cpu",
            )
            self.dimension = self._model.get_sentence_embedding_dimension()
            self.is_fallback = False

        except Exception:
            # Fall back to hash-based embeddings
            if self.config.fallback_to_hash:
                self._fallback = HashEmbedding(
                    dimension=self.config.dimension,
                    normalize=self.config.normalize,
                )
                self.is_fallback = True
            else:
                raise

    def embed(self, text: str) -> list[float]:
        """
        Create embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        if self._model is not None:
            embedding = self._model.encode(
                text,
                normalize_embeddings=self.config.normalize,
            )
            return embedding.tolist()
        elif self._fallback is not None:
            return self._fallback.embed(text)
        else:
            raise RuntimeError("No embedding model available")

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """
        Create embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if self._model is not None:
            embeddings = self._model.encode(
                list(texts),
                normalize_embeddings=self.config.normalize,
                batch_size=self.config.batch_size,
            )
            return [e.tolist() for e in embeddings]
        elif self._fallback is not None:
            return self._fallback.embed_batch(texts)
        else:
            raise RuntimeError("No embedding model available")

    def similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity (0 to 1 for normalized embeddings)
        """
        arr1 = np.array(embedding1)
        arr2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))
