"""Dependency injection for the HTTP API."""

from functools import lru_cache
from typing import AsyncGenerator

from mind.storage.sqlite import SQLiteStorage
from mind.storage.embeddings import EmbeddingStore


# Global storage instances (initialized on first request)
_storage: SQLiteStorage | None = None
_embeddings: EmbeddingStore | None = None


async def get_storage() -> SQLiteStorage:
    """Get the SQLite storage instance.

    Creates and initializes storage on first call.
    """
    global _storage
    if _storage is None:
        _storage = SQLiteStorage()
        await _storage.initialize()
    return _storage


async def get_embeddings() -> EmbeddingStore:
    """Get the embedding store instance.

    Creates store on first call.
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = EmbeddingStore()
    return _embeddings


async def cleanup():
    """Cleanup storage connections on shutdown."""
    global _storage, _embeddings
    if _storage is not None:
        await _storage.close()
        _storage = None
    _embeddings = None


def reset_for_testing():
    """Reset global state for testing."""
    global _storage, _embeddings
    _storage = None
    _embeddings = None
