class ImplementationContextError(RuntimeError):
    """Base error for implementation context failures."""


class ImplementationContextConfigurationError(ImplementationContextError):
    """Raised when implementation context configuration is invalid."""


class ImplementationContextRetrievalError(ImplementationContextError):
    """Raised when implementation context cannot be retrieved."""
