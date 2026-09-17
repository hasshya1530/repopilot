from dataclasses import dataclass
from enum import StrEnum


class TestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class TestResult:
    status: TestStatus
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    tests_run: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == TestStatus.PASSED
