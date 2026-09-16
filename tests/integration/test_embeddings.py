import pytest

from ingestion.embeddings import EmbeddingError, OllamaEmbeddingProvider


@pytest.mark.asyncio
async def test_ollama_embedding_real_model() -> None:
    provider = OllamaEmbeddingProvider()

    embedding = await provider.embed(
        "def calculate_total(items): return sum(items)"
    )

    assert isinstance(embedding, list)
    assert len(embedding) == 768
    assert all(isinstance(value, float) for value in embedding)


@pytest.mark.asyncio
async def test_ollama_embedding_rejects_empty_text() -> None:
    provider = OllamaEmbeddingProvider()

    with pytest.raises(EmbeddingError, match="empty text"):
        await provider.embed("   ")
