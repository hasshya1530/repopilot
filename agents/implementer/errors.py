class ImplementationError(RuntimeError):
    """Base error for implementation failures."""


class ImplementationConfigurationError(ImplementationError):
    """Raised when implementation configuration is invalid."""


class ChangeParsingError(ImplementationError):
    """Raised when an LLM response cannot be parsed into code changes."""


class ImplementationGenerationError(ImplementationError):
    """Raised when implementation generation fails."""
