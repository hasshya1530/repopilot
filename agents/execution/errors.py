class ExecutionError(RuntimeError):
    """Base error for execution failures."""


class ExecutionConfigurationError(ExecutionError):
    """Raised when execution configuration is invalid."""


class ExecutionValidationError(ExecutionError):
    """Raised when execution inputs are invalid."""
