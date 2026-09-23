from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from agents.debugger.repair_models import RepairProposal
from agents.implementer.models import ChangeOperation


class RepairValidationCode(StrEnum):
    EMPTY_DIAGNOSIS = "empty_diagnosis"
    EMPTY_REPAIR = "empty_repair"
    INVALID_PATH = "invalid_path"
    PATH_TRAVERSAL = "path_traversal"
    DUPLICATE_FILE = "duplicate_file"
    INVALID_OPERATION = "invalid_operation"
    INVALID_CONTENT = "invalid_content"


@dataclass(frozen=True, slots=True)
class RepairValidationIssue:
    code: RepairValidationCode
    file_path: str
    message: str


@dataclass(frozen=True, slots=True)
class RepairValidationResult:
    valid: bool
    issues: tuple[RepairValidationIssue, ...]

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(issue.message for issue in self.issues)


class RepairValidator:
    """Validate LLM-generated debugger repairs before filesystem application."""

    def validate(
        self,
        proposal: RepairProposal,
    ) -> RepairValidationResult:
        issues: list[RepairValidationIssue] = []

        if not proposal.diagnosis.strip():
            issues.append(
                RepairValidationIssue(
                    code=RepairValidationCode.EMPTY_DIAGNOSIS,
                    file_path="",
                    message="Repair proposal diagnosis must not be empty.",
                )
            )

        if not proposal.changes:
            issues.append(
                RepairValidationIssue(
                    code=RepairValidationCode.EMPTY_REPAIR,
                    file_path="",
                    message="Repair proposal must contain at least one change.",
                )
            )

        seen_paths: set[str] = set()

        for change in proposal.changes:
            file_path = change.file_path

            if not file_path.strip():
                issues.append(
                    RepairValidationIssue(
                        code=RepairValidationCode.INVALID_PATH,
                        file_path=file_path,
                        message="Repair change path must not be empty.",
                    )
                )
                continue

            path = PurePosixPath(file_path.replace("\\", "/"))

            if path.is_absolute():
                issues.append(
                    RepairValidationIssue(
                        code=RepairValidationCode.INVALID_PATH,
                        file_path=file_path,
                        message=f"Repair path must be relative: {file_path}.",
                    )
                )

            if ".." in path.parts:
                issues.append(
                    RepairValidationIssue(
                        code=RepairValidationCode.PATH_TRAVERSAL,
                        file_path=file_path,
                        message=(
                            f"Repair path must not contain '..': {file_path}."
                        ),
                    )
                )

            if file_path in seen_paths:
                issues.append(
                    RepairValidationIssue(
                        code=RepairValidationCode.DUPLICATE_FILE,
                        file_path=file_path,
                        message=(
                            f"Repair contains multiple changes for the "
                            f"same file: {file_path}."
                        ),
                    )
                )

            seen_paths.add(file_path)

            if change.operation not in (
                ChangeOperation.CREATE,
                ChangeOperation.MODIFY,
                ChangeOperation.DELETE,
            ):
                issues.append(
                    RepairValidationIssue(
                        code=RepairValidationCode.INVALID_OPERATION,
                        file_path=file_path,
                        message=(
                            f"Unsupported repair operation: "
                            f"{change.operation.value}."
                        ),
                    )
                )
                continue

            if change.operation == ChangeOperation.DELETE:
                if change.content != "":
                    issues.append(
                        RepairValidationIssue(
                            code=RepairValidationCode.INVALID_CONTENT,
                            file_path=file_path,
                            message=(
                                f"DELETE repair must have empty content: "
                                f"{file_path}."
                            ),
                        )
                    )
            elif not change.content.strip():
                issues.append(
                    RepairValidationIssue(
                        code=RepairValidationCode.INVALID_CONTENT,
                        file_path=file_path,
                        message=(
                            f"{change.operation.value.upper()} repair must "
                            f"contain resulting file content: {file_path}."
                        ),
                    )
                )

        return RepairValidationResult(
            valid=not issues,
            issues=tuple(issues),
        )
