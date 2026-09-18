from dataclasses import dataclass
from enum import StrEnum


class TestStatus(StrEnum):
    """Outcome of a test execution."""

    __test__ = False

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class TestResult:
    """Structured result produced by the test runner."""

    __test__ = False

    status: TestStatus
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    test_count: int | None = None
    failure_count: int | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the test execution succeeded."""
        return self.status is TestStatus.PASSED
