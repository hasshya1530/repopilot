class ChangeApplicationError(RuntimeError):
    """Base error for change application failures."""


class ChangeApplicationConfigurationError(ChangeApplicationError):
    """Raised when the change applier configuration is invalid."""


class ChangeApplicationValidationError(ChangeApplicationError):
    """Raised when a requested change is unsafe or invalid."""


class ChangeApplicationConflictError(ChangeApplicationError):
    """Raised when a requested change conflicts with the workspace state."""
