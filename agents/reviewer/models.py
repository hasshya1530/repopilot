from dataclasses import dataclass
from enum import StrEnum


class ReviewSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewCategory(StrEnum):
    CORRECTNESS = "correctness"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    CODE_QUALITY = "code_quality"
    TEST_COVERAGE = "test_coverage"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    severity: ReviewSeverity
    category: ReviewCategory
    file_path: str
    line: int | None
    title: str
    description: str
    recommendation: str


@dataclass(frozen=True, slots=True)
class ReviewResult:
    decision: ReviewDecision
    summary: str
    findings: tuple[ReviewFinding, ...]

    @property
    def approved(self) -> bool:
        return self.decision == ReviewDecision.APPROVE

    @property
    def blocking_findings(self) -> tuple[ReviewFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity
            in {
                ReviewSeverity.HIGH,
                ReviewSeverity.CRITICAL,
            }
        )
