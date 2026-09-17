class DebuggerError(RuntimeError):
    """Base exception for self-debugging failures."""


class DebuggerConfigurationError(DebuggerError):
    """Raised when debugger configuration is invalid."""


class RepairGenerationError(DebuggerError):
    """Raised when a repair cannot be generated."""


class RepairLimitExceededError(DebuggerError):
    """Raised when the maximum repair attempts are exhausted."""
