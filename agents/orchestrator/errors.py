class OrchestrationError(RuntimeError):
    """Base exception for orchestration failures."""


class InvalidOrchestrationTransitionError(
    OrchestrationError,
    ValueError,
):
    """Raised when an invalid orchestration state transition is requested."""


class OrchestrationConfigurationError(OrchestrationError):
    """Raised when orchestration is configured incorrectly."""


class OrchestrationCancelledError(OrchestrationError):
    """Raised when orchestration is cancelled."""


class OrchestrationExecutionError(OrchestrationError):
    """Raised when orchestration execution fails."""
