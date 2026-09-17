from dataclasses import dataclass
from enum import StrEnum

from agents.implementer.applier.models import ChangeApplicationResult
from agents.testing.models import TestResult


class ExecutionStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    TEST_ERROR = "test_error"


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    status: ExecutionStatus
    changes: ChangeApplicationResult
    tests: TestResult

    @property
    def succeeded(self) -> bool:
        return self.status == ExecutionStatus.PASSED
