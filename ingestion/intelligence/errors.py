class IntelligenceError(Exception):
    """Base exception for repository intelligence errors."""


class IntelligenceConfigurationError(IntelligenceError):
    """Raised when repository intelligence is configured incorrectly."""


class IntelligenceAggregationError(IntelligenceError):
    """Raised when repository intelligence cannot be aggregated."""
