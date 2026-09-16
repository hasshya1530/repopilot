class GraphError(Exception):
    """Base exception for repository graph errors."""


class GraphConfigurationError(GraphError):
    """Raised when repository graph configuration is invalid."""


class GraphBuildError(GraphError):
    """Raised when a repository graph cannot be built."""
