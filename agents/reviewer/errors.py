class ReviewerError(RuntimeError):
    """Base exception for code review failures."""


class ReviewConfigurationError(ReviewerError):
    """Raised when reviewer configuration is invalid."""


class ReviewParsingError(ReviewerError):
    """Raised when an LLM review cannot be parsed."""


class ReviewGenerationError(ReviewerError):
    """Raised when an LLM review cannot be generated."""
