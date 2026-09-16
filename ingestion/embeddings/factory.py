from apps.api.app.core.config import Settings
from ingestion.embeddings.base import EmbeddingProvider
from ingestion.embeddings.errors import EmbeddingConfigurationError
from ingestion.embeddings.providers import OllamaEmbeddingProvider


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Create the configured embedding provider."""

    provider = settings.embedding_provider.lower().strip()
    model = settings.embedding_model.strip()

    if provider == "ollama":
        if not model:
            raise EmbeddingConfigurationError(
                "EMBEDDING_MODEL must be configured when using Ollama."
            )

        return OllamaEmbeddingProvider(
            model_name=model,
            base_url=settings.ollama_base_url,
        )

    raise EmbeddingConfigurationError(
        f"Unsupported embedding provider: {settings.embedding_provider}"
    )
