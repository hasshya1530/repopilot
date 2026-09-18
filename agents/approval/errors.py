class ApprovalError(RuntimeError):
    """Base exception for approval workflow failures."""


class ApprovalNotFoundError(ApprovalError):
    """Raised when the requested pull request does not exist."""


class InvalidApprovalTransitionError(ApprovalError):
    """Raised when an approval state transition is not permitted."""


class ApprovalRequiredError(ApprovalError):
    """Raised when a downstream operation requires human approval."""
