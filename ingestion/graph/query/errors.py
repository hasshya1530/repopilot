class GraphQueryError(Exception):
    """Base exception for graph query failures."""


class GraphQueryConfigurationError(GraphQueryError):
    """Raised when graph query configuration is invalid."""


class SymbolQueryError(GraphQueryError):
    """Raised when symbol lookup fails."""
