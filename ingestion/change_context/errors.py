class ChangeContextError(Exception):
    """Base exception for repository change context errors."""


class ChangeContextConfigurationError(ChangeContextError):
    """Raised when change context configuration is invalid."""


class ChangeContextRetrievalError(ChangeContextError):
    """Raised when repository context retrieval fails."""


class ChangeContextAnalysisError(ChangeContextError):
    """Raised when dependency or impact analysis fails."""
