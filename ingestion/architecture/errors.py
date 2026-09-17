class ArchitectureError(Exception):
    """Base exception for architecture analysis."""


class ArchitectureConfigurationError(ArchitectureError):
    """Raised when architecture analysis is incorrectly configured."""


class ArchitectureAggregationError(ArchitectureError):
    """Raised when repository architecture cannot be aggregated."""
