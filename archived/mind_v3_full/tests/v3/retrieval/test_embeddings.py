"""Tests for embedding service."""
import pytest
import numpy as np

from mind.v3.retrieval.embeddings import (
    EmbeddingService,
    EmbeddingConfig,
    HashEmbedding,
)


class TestEmbeddingConfig:
    """Test EmbeddingConfig settings."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = EmbeddingConfig()

        assert config.model_name == "all-MiniLM-L6-v2"
        assert config.dimension == 384
        assert config.use_gpu is False
        assert config.normalize is True

    def test_custom_config(self):
        """Should accept custom settings."""
        config = EmbeddingConfig(
            model_name="all-mpnet-base-v2",
            dimension=768,
            use_gpu=True,
        )

        assert config.model_name == "all-mpnet-base-v2"
        assert config.dimension == 768
        assert config.use_gpu is True


class TestHashEmbedding:
    """Test HashEmbedding fallback."""

    def test_create_hash_embedding(self):
        """Should create hash embedding service."""
        service = HashEmbedding(dimension=384)

        assert service is not None
        assert service.dimension == 384

    def test_embed_single_text(self):
        """Should embed single text."""
        service = HashEmbedding(dimension=384)

        embedding = service.embed("Hello world")

        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_deterministic(self):
        """Same text should produce same embedding."""
        service = HashEmbedding(dimension=384)

        emb1 = service.embed("Hello world")
        emb2 = service.embed("Hello world")

        assert emb1 == emb2

    def test_embed_different_texts(self):
        """Different texts should produce different embeddings."""
        service = HashEmbedding(dimension=384)

        emb1 = service.embed("Hello world")
        emb2 = service.embed("Goodbye world")

        assert emb1 != emb2

    def test_embed_batch(self):
        """Should embed multiple texts."""
        service = HashEmbedding(dimension=384)

        embeddings = service.embed_batch([
            "First text",
            "Second text",
            "Third text",
        ])

        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)

    def test_embed_normalized(self):
        """Embeddings should be normalized by default."""
        service = HashEmbedding(dimension=384, normalize=True)

        embedding = service.embed("Test text")
        norm = np.linalg.norm(embedding)

        assert abs(norm - 1.0) < 0.01  # Should be unit length


class TestEmbeddingService:
    """Test EmbeddingService."""

    def test_create_service_default(self):
        """Should create service with defaults."""
        service = EmbeddingService()

        assert service is not None
        assert service.dimension == 384

    def test_create_service_with_config(self):
        """Should create service with config."""
        config = EmbeddingConfig(dimension=384)
        service = EmbeddingService(config=config)

        assert service.dimension == 384

    def test_embed_single_text(self):
        """Should embed single text."""
        service = EmbeddingService()

        embedding = service.embed("Hello world")

        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_batch(self):
        """Should embed multiple texts."""
        service = EmbeddingService()

        embeddings = service.embed_batch([
            "First text",
            "Second text",
        ])

        assert len(embeddings) == 2

    def test_embed_empty_text(self):
        """Should handle empty text."""
        service = EmbeddingService()

        embedding = service.embed("")

        assert len(embedding) == 384

    def test_similarity_similar_texts(self):
        """Similar texts should have high similarity."""
        service = EmbeddingService()

        emb1 = service.embed("I love programming in Python")
        emb2 = service.embed("I enjoy coding in Python")

        similarity = service.similarity(emb1, emb2)

        # Should be reasonably similar
        assert similarity > 0.5

    def test_similarity_different_texts(self):
        """Different texts should have lower similarity."""
        service = EmbeddingService()

        emb1 = service.embed("I love programming in Python")
        emb2 = service.embed("The weather is sunny today")

        similarity = service.similarity(emb1, emb2)

        # Should be less similar than related texts
        assert similarity < 0.8

    def test_similarity_identical_texts(self):
        """Identical texts should have similarity close to 1."""
        service = EmbeddingService()

        text = "I love programming"
        emb1 = service.embed(text)
        emb2 = service.embed(text)

        similarity = service.similarity(emb1, emb2)

        assert similarity > 0.99


class TestEmbeddingServiceFallback:
    """Test fallback behavior."""

    def test_uses_hash_when_model_unavailable(self):
        """Should fall back to hash embedding if model fails."""
        # Use a non-existent model to trigger fallback
        config = EmbeddingConfig(
            model_name="nonexistent-model-xyz",
            fallback_to_hash=True,
        )
        service = EmbeddingService(config=config)

        # Should still work via fallback
        embedding = service.embed("Test text")
        assert len(embedding) == 384

    def test_is_using_fallback(self):
        """Should report when using fallback."""
        config = EmbeddingConfig(
            model_name="nonexistent-model-xyz",
            fallback_to_hash=True,
        )
        service = EmbeddingService(config=config)

        assert service.is_fallback is True
