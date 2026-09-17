from dataclasses import dataclass
from enum import StrEnum


class AppliedChangeStatus(StrEnum):
    APPLIED = "applied"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class AppliedChange:
    file_path: str
    status: AppliedChangeStatus
    operation: str
    diff: str


@dataclass(frozen=True, slots=True)
class ChangeApplicationResult:
    changes: tuple[AppliedChange, ...]
    files_changed: int
    dry_run: bool
