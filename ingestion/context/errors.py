class ContextError(Exception):
    """Base exception for repository context errors."""


class ContextConfigurationError(ContextError):
    """Raised when repository context is configured incorrectly."""


class ContextRetrievalError(ContextError):
    """Raised when repository context retrieval fails."""
