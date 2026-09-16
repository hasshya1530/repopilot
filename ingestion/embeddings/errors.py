class EmbeddingError(Exception):
    """Base exception for embedding failures."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when an embedding provider is incorrectly configured."""
