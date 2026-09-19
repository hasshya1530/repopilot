from __future__ import annotations

import asyncio

from ollama import AsyncClient

from apps.api.app.core.config import get_settings
from ingestion.embeddings.base import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by a local Ollama server."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model_name: str | None = None,
        dimension: int | None = None,
        timeout_seconds: float = 120.0,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings()

        resolved_base_url = (
            base_url.strip()
            if base_url is not None
            else settings.ollama_base_url
        )
        resolved_model_name = (
            model_name.strip()
            if model_name is not None
            else settings.embedding_model.strip()
        )

        if not resolved_base_url:
            raise ValueError("Ollama base URL must not be empty.")

        if not resolved_model_name:
            raise ValueError("Ollama embedding model must not be empty.")

        self._client = AsyncClient(
            host=resolved_base_url,
            timeout=timeout_seconds,
        )
        self._model_name = resolved_model_name
        self._dimension = (
            dimension
            if dimension is not None
            else settings.vector_dimension or 768
        )
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    @property
    def model_name(self) -> str:
        """Return the configured Ollama embedding model."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimensionality."""
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        embeddings = await self.embed_many([text])
        return embeddings[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts using Ollama."""
        if not texts:
            return []

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    self._client.embed(
                        model=self._model_name,
                        input=texts,
                    ),
                    timeout=self._timeout_seconds,
                )

                embeddings = [
                    list(embedding)
                    for embedding in response.embeddings
                ]

                if len(embeddings) != len(texts):
                    raise RuntimeError(
                        "Ollama returned an unexpected number of embeddings: "
                        f"expected {len(texts)}, got {len(embeddings)}."
                    )

                for index, embedding in enumerate(embeddings):
                    if len(embedding) != self._dimension:
                        raise RuntimeError(
                            "Ollama returned an unexpected embedding dimension: "
                            f"expected {self._dimension}, "
                            f"got {len(embedding)} for item {index}."
                        )

                return embeddings

            except Exception as exc:
                last_error = exc

                if attempt >= self._max_retries:
                    break

                await asyncio.sleep(2**attempt)

        raise RuntimeError(
            "Ollama embedding request failed after "
            f"{self._max_retries + 1} attempts for "
            f"{len(texts)} texts using model '{self._model_name}'."
        ) from last_error
