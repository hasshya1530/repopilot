class TestRunnerError(RuntimeError):
    """Base error for test runner failures."""


class TestRunnerConfigurationError(TestRunnerError):
    """Raised when test runner configuration is invalid."""


class TestDetectionError(TestRunnerError):
    """Raised when repository test detection fails."""
