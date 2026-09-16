from ingestion.chunker.models import CodeChunk
from ingestion.embeddings.base import EmbeddingProvider


class EmbeddingService:
    """Generate and attach embeddings to code chunks."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    async def embed_chunk(self, chunk: CodeChunk) -> list[float]:
        """Generate an embedding for a single code chunk."""

        return await self._provider.embed(chunk.content)

    async def embed_chunks(
        self,
        chunks: list[CodeChunk],
    ) -> list[list[float]]:
        """Generate embeddings for multiple code chunks."""

        if not chunks:
            return []

        texts = [chunk.content for chunk in chunks]
        return await self._provider.embed_many(texts)
