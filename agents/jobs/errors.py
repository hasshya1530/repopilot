class JobError(RuntimeError):
    """Base error for background job execution."""


class RetryableJobError(JobError):
    """Raised when a job failure may succeed on a later retry."""


class NonRetryableJobError(JobError):
    """Raised when a job failure must not be retried."""
