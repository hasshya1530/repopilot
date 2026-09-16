from ollama import AsyncClient

from ingestion.embeddings.base import EmbeddingProvider
from ingestion.embeddings.errors import EmbeddingError


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by Ollama."""

    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        dimension: int = 768,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._client = AsyncClient(host=base_url)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingError("Cannot embed empty text.")

        try:
            response = await self._client.embed(
                model=self._model_name,
                input=text,
            )
        except Exception as exc:
            raise EmbeddingError(f"Failed to generate embedding with {self._model_name}") from exc

        embeddings = response["embeddings"]

        if not embeddings:
            raise EmbeddingError("Ollama returned no embeddings.")

        embedding = embeddings[0]

        if len(embedding) != self._dimension:
            raise EmbeddingError(
                f"Expected embedding dimension {self._dimension}, got {len(embedding)}"
            )

        return list(embedding)
