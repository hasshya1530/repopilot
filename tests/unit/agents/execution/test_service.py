from pathlib import Path

import pytest

from agents.execution.errors import ExecutionValidationError
from agents.execution.models import ExecutionResult, ExecutionStatus
from agents.execution.service import ExecutionService
from agents.implementer.applier.models import (
    AppliedChange,
    AppliedChangeStatus,
    ChangeApplicationResult,
)
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from agents.testing.models import TestResult as TestingResult
from agents.testing.models import TestStatus as TestingStatus


class FakeApplier:
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self.applied_implementation: ImplementationResult | None = None

    def apply(
        self,
        implementation: ImplementationResult,
    ) -> ChangeApplicationResult:
        self.applied_implementation = implementation

        applied_changes = tuple(
            AppliedChange(
                file_path=change.file_path,
                status=AppliedChangeStatus.APPLIED,
                operation=change.operation.value,
                diff="",
            )
            for change in implementation.changes
        )

        return ChangeApplicationResult(
            changes=applied_changes,
            files_changed=len(applied_changes),
            dry_run=False,
        )


class FakeTestRunner:
    def __init__(self, result: TestingResult) -> None:
        self.result = result
        self.received_workspace: Path | None = None

    def run(self, repository_path: Path) -> TestingResult:
        self.received_workspace = repository_path
        return self.result


def make_implementation() -> ImplementationResult:
    return ImplementationResult(
        summary="Implement requested change",
        changes=(
            CodeChange(
                file_path="example.py",
                operation=ChangeOperation.MODIFY,
                content="print('updated')\n",
                reason="Update example implementation",
            ),
        ),
    )


def make_test_result(
    status: TestingStatus,
    exit_code: int = 0,
) -> TestingResult:
    return TestingResult(
        status=status,
        command=("pytest", "-q"),
        exit_code=exit_code,
        stdout="1 passed\n" if status == TestingStatus.PASSED else "",
        stderr="",
        duration_seconds=0.1,
    )


def test_execute_applies_changes_and_runs_tests(tmp_path: Path) -> None:
    runner = FakeTestRunner(
        make_test_result(TestingStatus.PASSED),
    )

    service = ExecutionService(
        change_applier_factory=FakeApplier,
        test_runner=runner,
    )

    implementation = make_implementation()

    result = service.execute(
        tmp_path,
        implementation,
    )

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.PASSED
    assert result.succeeded is True
    assert result.changes.files_changed == 1
    assert len(result.changes.changes) == 1
    assert result.changes.changes[0].status == AppliedChangeStatus.APPLIED
    assert result.tests.status == TestingStatus.PASSED
    assert runner.received_workspace == tmp_path.resolve()


def test_execute_returns_failed_when_tests_fail(tmp_path: Path) -> None:
    runner = FakeTestRunner(
        make_test_result(
            TestingStatus.FAILED,
            exit_code=1,
        ),
    )

    service = ExecutionService(
        change_applier_factory=FakeApplier,
        test_runner=runner,
    )

    result = service.execute(
        tmp_path,
        make_implementation(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.succeeded is False
    assert result.tests.status == TestingStatus.FAILED
    assert result.tests.exit_code == 1


def test_execute_returns_failed_when_tests_error(tmp_path: Path) -> None:
    runner = FakeTestRunner(
        make_test_result(
            TestingStatus.ERROR,
            exit_code=2,
        ),
    )

    service = ExecutionService(
        change_applier_factory=FakeApplier,
        test_runner=runner,
    )

    result = service.execute(
        tmp_path,
        make_implementation(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.succeeded is False
    assert result.tests.status == TestingStatus.ERROR


def test_execute_rejects_missing_workspace(tmp_path: Path) -> None:
    runner = FakeTestRunner(
        make_test_result(TestingStatus.PASSED),
    )

    service = ExecutionService(
        change_applier_factory=FakeApplier,
        test_runner=runner,
    )

    missing_workspace = tmp_path / "missing"

    with pytest.raises(
        ExecutionValidationError,
        match="Workspace does not exist",
    ):
        service.execute(
            missing_workspace,
            make_implementation(),
        )
