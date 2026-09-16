import pytest

from ingestion.embeddings import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    @property
    def model_name(self) -> str:
        return "fake-model"

    @property
    def dimension(self) -> int:
        return 3

    async def embed(self, text: str) -> list[float]:
        return [float(len(text)), 1.0, 2.0]


@pytest.mark.asyncio
async def test_embedding_provider_exposes_model_metadata() -> None:
    provider = FakeEmbeddingProvider()

    assert provider.model_name == "fake-model"
    assert provider.dimension == 3


@pytest.mark.asyncio
async def test_embedding_provider_embeds_single_text() -> None:
    provider = FakeEmbeddingProvider()

    result = await provider.embed("hello")

    assert result == [5.0, 1.0, 2.0]


@pytest.mark.asyncio
async def test_embedding_provider_embeds_multiple_texts() -> None:
    provider = FakeEmbeddingProvider()

    result = await provider.embed_many(["hi", "hello"])

    assert result == [
        [2.0, 1.0, 2.0],
        [5.0, 1.0, 2.0],
    ]
