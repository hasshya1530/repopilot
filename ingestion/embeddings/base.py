from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Interface for text embedding providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the embedding model identifier."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of generated embeddings."""
        raise NotImplementedError

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        raise NotImplementedError

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]
