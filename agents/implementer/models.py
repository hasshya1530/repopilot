from dataclasses import dataclass
from enum import StrEnum


class ChangeOperation(StrEnum):
    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class CodeChange:
    file_path: str
    operation: ChangeOperation
    content: str
    reason: str


@dataclass(frozen=True, slots=True)
class ImplementationResult:
    summary: str
    changes: tuple[CodeChange, ...]
