from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agents.implementer.models import ChangeOperation, ImplementationResult
from agents.planner.plan_models import ImplementationPlan, PlanStepType


class ImplementationValidationCode(StrEnum):
    UNPLANNED_FILE = "unplanned_file"
    INVALID_OPERATION = "invalid_operation"
    MISSING_PLANNED_FILE = "missing_planned_file"
    DUPLICATE_FILE = "duplicate_file"
    MISSING_TEST_CHANGE = "missing_test_change"


@dataclass(frozen=True, slots=True)
class ImplementationValidationIssue:
    code: ImplementationValidationCode
    file_path: str
    message: str


@dataclass(frozen=True, slots=True)
class ImplementationValidationResult:
    valid: bool
    issues: tuple[ImplementationValidationIssue, ...]

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(issue.message for issue in self.issues)


class ImplementationValidator:
    """Validate generated implementation changes against the approved plan."""

    def validate(
        self,
        *,
        plan: ImplementationPlan,
        implementation: ImplementationResult,
    ) -> ImplementationValidationResult:
        planned_operations = self._planned_operations(plan)

        issues: list[ImplementationValidationIssue] = []
        seen_paths: set[str] = set()

        for change in implementation.changes:
            file_path = change.file_path

            if file_path in seen_paths:
                issues.append(
                    ImplementationValidationIssue(
                        code=ImplementationValidationCode.DUPLICATE_FILE,
                        file_path=file_path,
                        message=(
                            f"Implementation contains multiple changes for "
                            f"the same file: {file_path}."
                        ),
                    )
                )

            seen_paths.add(file_path)

            allowed_operations = planned_operations.get(file_path)

            if allowed_operations is None:
                issues.append(
                    ImplementationValidationIssue(
                        code=ImplementationValidationCode.UNPLANNED_FILE,
                        file_path=file_path,
                        message=(
                            f"Implementation changes unplanned file: "
                            f"{file_path}."
                        ),
                    )
                )
                continue

            if change.operation not in allowed_operations:
                allowed = ", ".join(
                    sorted(operation.value for operation in allowed_operations)
                )

                issues.append(
                    ImplementationValidationIssue(
                        code=ImplementationValidationCode.INVALID_OPERATION,
                        file_path=file_path,
                        message=(
                            f"Operation {change.operation.value!r} is not "
                            f"allowed for {file_path}; expected one of: {allowed}."
                        ),
                    )
                )

        changed_paths = {
            change.file_path
            for change in implementation.changes
        }

        for file_path, allowed_operations in planned_operations.items():
            if file_path not in changed_paths:
                operation_names = ", ".join(
                    sorted(operation.value for operation in allowed_operations)
                )

                issues.append(
                    ImplementationValidationIssue(
                        code=ImplementationValidationCode.MISSING_PLANNED_FILE,
                        file_path=file_path,
                        message=(
                            f"Implementation did not produce the planned "
                            f"change for {file_path}; expected operation(s): "
                            f"{operation_names}."
                        ),
                    )
                )

        issues.extend(
            self._validate_test_requirements(
                plan=plan,
                implementation=implementation,
            )
        )

        return ImplementationValidationResult(
            valid=not issues,
            issues=tuple(issues),
        )

    @staticmethod
    def _validate_test_requirements(
        *,
        plan: ImplementationPlan,
        implementation: ImplementationResult,
    ) -> tuple[ImplementationValidationIssue, ...]:
        has_test_step = any(
            step.step_type is PlanStepType.TEST
            for step in plan.implementation_steps
        )

        if not has_test_step and not plan.tests_to_add:
            return ()

        test_changes = tuple(
            change
            for change in implementation.changes
            if ImplementationValidator._looks_like_test_path(
                change.file_path
            )
        )

        if test_changes:
            return ()

        return (
            ImplementationValidationIssue(
                code=ImplementationValidationCode.MISSING_TEST_CHANGE,
                file_path="",
                message=(
                    "The approved plan requires test coverage, but the "
                    "implementation produced no test-file change."
                ),
            ),
        )

    @staticmethod
    def _looks_like_test_path(file_path: str) -> bool:
        normalized = file_path.replace("\\", "/").lower()
        name = normalized.rsplit("/", 1)[-1]

        return (
            normalized.startswith("tests/")
            or "/tests/" in normalized
            or name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".test.ts")
            or name.endswith(".test.tsx")
            or name.endswith(".spec.ts")
            or name.endswith(".spec.tsx")
            or name.endswith(".spec.js")
            or name.endswith(".spec.jsx")
        )

    @staticmethod
    def _planned_operations(
        plan: ImplementationPlan,
    ) -> dict[str, frozenset[ChangeOperation]]:
        operations: dict[str, set[ChangeOperation]] = {}

        for item in plan.files_to_modify:
            operations.setdefault(item.file_path, set()).add(
                ChangeOperation.MODIFY
            )

        for item in plan.files_to_create:
            operations.setdefault(item.file_path, set()).add(
                ChangeOperation.CREATE
            )

        # Test files are first-class implementation targets.
        # Their filesystem operation is inferred from the plan's
        # create/modify classification when present in the main file lists.
        #
        # If a test file appears only in test_files, it must be modified
        # when it already exists and created when it does not.
        for item in plan.test_files:
            if item.file_path not in operations:
                operations.setdefault(item.file_path, set()).add(
                    ChangeOperation.MODIFY
                )

        return {
            file_path: frozenset(file_operations)
            for file_path, file_operations in operations.items()
        }
