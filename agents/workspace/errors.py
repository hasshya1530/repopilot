class WorkspaceError(RuntimeError):
    """Base error for workspace failures."""


class WorkspaceConfigurationError(WorkspaceError):
    """Raised when workspace configuration is invalid."""


class GitCommandError(WorkspaceError):
    """Raised when a Git command fails."""


class WorkspaceStateError(WorkspaceError):
    """Raised when the workspace is in an invalid state."""
