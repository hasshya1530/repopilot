from dataclasses import dataclass
from enum import StrEnum

from agents.implementer.models import CodeChange
from agents.testing.models import TestResult


class DebuggerStatus(StrEnum):
    FIXED = "fixed"
    FAILED = "failed"
    LIMIT_REACHED = "limit_reached"


@dataclass(frozen=True, slots=True)
class FailureContext:
    test_result: TestResult
    attempt: int


@dataclass(frozen=True, slots=True)
class RepairAttempt:
    attempt: int
    diagnosis: str
    changes: tuple[CodeChange, ...]
    test_result: TestResult


@dataclass(frozen=True, slots=True)
class DebuggerResult:
    status: DebuggerStatus
    attempts: tuple[RepairAttempt, ...]
    final_test_result: TestResult

    @property
    def succeeded(self) -> bool:
        return self.status == DebuggerStatus.FIXED
