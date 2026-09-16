from apps.api.app.core.config import Settings
from ingestion.embeddings import (
    EmbeddingConfigurationError,
    OllamaEmbeddingProvider,
    create_embedding_provider,
)


def test_create_ollama_embedding_provider() -> None:
    settings = Settings(
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        ollama_base_url="http://localhost:11434",
    )

    provider = create_embedding_provider(settings)

    assert isinstance(provider, OllamaEmbeddingProvider)
    assert provider.model_name == "nomic-embed-text"
    assert provider.dimension == 768


def test_create_embedding_provider_rejects_missing_model() -> None:
    settings = Settings(
        embedding_provider="ollama",
        embedding_model="",
        ollama_base_url="http://localhost:11434",
    )

    try:
        create_embedding_provider(settings)
    except EmbeddingConfigurationError as exc:
        assert "EMBEDDING_MODEL" in str(exc)
    else:
        raise AssertionError("Expected EmbeddingConfigurationError")


def test_create_embedding_provider_rejects_unknown_provider() -> None:
    settings = Settings(
        embedding_provider="unknown",
        embedding_model="some-model",
    )

    try:
        create_embedding_provider(settings)
    except EmbeddingConfigurationError as exc:
        assert "Unsupported embedding provider" in str(exc)
    else:
        raise AssertionError("Expected EmbeddingConfigurationError")
