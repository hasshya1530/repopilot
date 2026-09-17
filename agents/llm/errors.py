class LLMError(Exception):
    """Base exception for LLM operations."""


class LLMConfigurationError(LLMError):
    """Raised when the LLM configuration is invalid."""


class LLMRequestError(LLMError):
    """Raised when an LLM request fails."""


class LLMResponseError(LLMError):
    """Raised when an LLM response is invalid or unusable."""
