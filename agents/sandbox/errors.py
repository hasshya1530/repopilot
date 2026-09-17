class SandboxError(RuntimeError):
    """Base error for sandbox failures."""


class SandboxConfigurationError(SandboxError):
    """Raised when sandbox configuration is invalid."""


class SandboxExecutionError(SandboxError):
    """Raised when sandbox execution cannot be started."""
