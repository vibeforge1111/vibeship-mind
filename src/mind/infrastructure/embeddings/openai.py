"""OpenAI embedding generation."""

from functools import lru_cache

import httpx
import structlog

from mind.config import get_settings
from mind.core.errors import ErrorCode, MindError, Result

logger = structlog.get_logger()


class OpenAIEmbedder:
    """Generate embeddings using OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ):
        settings = get_settings()
        self._api_key = api_key or (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else None
        )
        self._model = model or settings.embedding_model
        self._dimensions = dimensions or settings.embedding_dimensions
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.openai.com/v1",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def embed(self, text: str) -> Result[list[float]]:
        """Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            Result with embedding vector or error
        """
        if not self._api_key:
            return Result.err(
                MindError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="OpenAI API key not configured",
                )
            )

        result = await self.embed_batch([text])
        if result.is_err:
            return Result.err(result.error)

        return Result.ok(result.value[0])

    async def embed_batch(self, texts: list[str]) -> Result[list[list[float]]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            Result with list of embedding vectors or error
        """
        if not self._api_key:
            return Result.err(
                MindError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="OpenAI API key not configured",
                )
            )

        if not texts:
            return Result.ok([])

        log = logger.bind(
            model=self._model,
            text_count=len(texts),
        )

        try:
            client = await self._get_client()

            response = await client.post(
                "/embeddings",
                json={
                    "input": texts,
                    "model": self._model,
                    "dimensions": self._dimensions,
                },
            )

            if response.status_code != 200:
                log.error(
                    "embedding_api_error",
                    status=response.status_code,
                    body=response.text[:200],
                )
                return Result.err(
                    MindError(
                        code=ErrorCode.VECTOR_SEARCH_FAILED,
                        message=f"OpenAI API error: {response.status_code}",
                    )
                )

            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]

            log.debug(
                "embeddings_generated",
                count=len(embeddings),
                dimensions=len(embeddings[0]) if embeddings else 0,
            )

            return Result.ok(embeddings)

        except httpx.TimeoutException:
            log.error("embedding_timeout")
            return Result.err(
                MindError(
                    code=ErrorCode.VECTOR_SEARCH_FAILED,
                    message="OpenAI API timeout",
                )
            )
        except Exception as e:
            log.error("embedding_error", error=str(e))
            return Result.err(
                MindError(
                    code=ErrorCode.VECTOR_SEARCH_FAILED,
                    message=f"Embedding generation failed: {e}",
                )
            )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global embedder instance
_embedder: OpenAIEmbedder | None = None


def get_embedder() -> OpenAIEmbedder:
    """Get or create embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = OpenAIEmbedder()
    return _embedder


async def close_embedder() -> None:
    """Close embedder client."""
    global _embedder
    if _embedder:
        await _embedder.close()
        _embedder = None
