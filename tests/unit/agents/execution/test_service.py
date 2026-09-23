from pathlib import Path

import pytest

from agents.execution.errors import ExecutionValidationError
from agents.execution.models import ExecutionResult, ExecutionStatus
from agents.execution.service import ExecutionService
from agents.implementer.applier.errors import ChangeApplicationValidationError
from agents.implementer.applier.models import (
    AppliedChangeStatus,
    ChangeApplicationResult,
)
from agents.implementer.applier.service import ChangeApplier
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
            __import__(
                "agents.implementer.applier.models",
                fromlist=["AppliedChange"],
            ).AppliedChange(
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


class RecordingTestRunner:
    def __init__(self, result: TestingResult) -> None:
        self.result = result
        self.received_workspace: Path | None = None
        self.received_command: str | None = None

    def run(
        self,
        repository_path: Path,
        validation_command: str | None = None,
    ) -> TestingResult:
        self.received_workspace = repository_path
        self.received_command = validation_command
        return self.result


class InspectingTestRunner:
    def __init__(self, result: TestingResult, file_path: str) -> None:
        self.result = result
        self.file_path = file_path
        self.received_workspace: Path | None = None
        self.observed_content: str | None = None

    def run(
        self,
        repository_path: Path,
        validation_command: str | None = None,
    ) -> TestingResult:
        self.received_workspace = repository_path
        self.observed_content = (
            repository_path / self.file_path
        ).read_text(encoding="utf-8")
        return self.result


class FailingApplier:
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path

    def apply(
        self,
        implementation: ImplementationResult,
    ) -> ChangeApplicationResult:
        raise ChangeApplicationValidationError(
            "Rejected implementation change."
        )


class RecordingRunner:
    def __init__(self, result: TestingResult) -> None:
        self.result = result
        self.called = False

    def run(
        self,
        repository_path: Path,
        validation_command: str | None = None,
    ) -> TestingResult:
        self.called = True
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


def test_execute_applies_changes_and_runs_tests(
    tmp_path: Path,
) -> None:
    runner = RecordingTestRunner(
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


def test_execute_returns_failed_when_tests_fail(
    tmp_path: Path,
) -> None:
    runner = RecordingTestRunner(
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


def test_execute_returns_failed_when_tests_error(
    tmp_path: Path,
) -> None:
    runner = RecordingTestRunner(
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


def test_execute_rejects_missing_workspace(
    tmp_path: Path,
) -> None:
    runner = RecordingTestRunner(
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


def test_execute_applies_real_changes_before_running_tests(
    tmp_path: Path,
) -> None:
    source = tmp_path / "example.py"
    source.write_text(
        "print('original')\n",
        encoding="utf-8",
    )

    runner = InspectingTestRunner(
        make_test_result(TestingStatus.PASSED),
        "example.py",
    )

    service = ExecutionService(
        change_applier_factory=ChangeApplier,
        test_runner=runner,
    )

    result = service.execute(
        tmp_path,
        make_implementation(),
    )

    assert result.status == ExecutionStatus.PASSED
    assert result.changes.files_changed == 1
    assert source.read_text(encoding="utf-8") == "print('updated')\n"
    assert runner.observed_content == "print('updated')\n"
    assert runner.received_workspace == tmp_path.resolve()


def test_execute_applies_create_change_before_running_tests(
    tmp_path: Path,
) -> None:
    implementation = ImplementationResult(
        summary="Create requested file",
        changes=(
            CodeChange(
                file_path="src/generated.py",
                operation=ChangeOperation.CREATE,
                content="VALUE = 42\n",
                reason="Create generated module.",
            ),
        ),
    )

    runner = InspectingTestRunner(
        make_test_result(TestingStatus.PASSED),
        "src/generated.py",
    )

    service = ExecutionService(
        change_applier_factory=ChangeApplier,
        test_runner=runner,
    )

    result = service.execute(
        tmp_path,
        implementation,
    )

    created = tmp_path / "src/generated.py"

    assert result.status == ExecutionStatus.PASSED
    assert result.changes.files_changed == 1
    assert created.exists()
    assert created.read_text(encoding="utf-8") == "VALUE = 42\n"
    assert runner.observed_content == "VALUE = 42\n"


def test_execute_does_not_run_tests_when_change_application_fails(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(
        make_test_result(TestingStatus.PASSED),
    )

    service = ExecutionService(
        change_applier_factory=FailingApplier,
        test_runner=runner,
    )

    with pytest.raises(
        ChangeApplicationValidationError,
        match="Rejected implementation change",
    ):
        service.execute(
            tmp_path,
            make_implementation(),
        )

    assert runner.called is False


def test_execute_passes_approved_validation_command_to_test_runner(
    tmp_path: Path,
) -> None:
    runner = RecordingTestRunner(
        make_test_result(TestingStatus.PASSED),
    )

    service = ExecutionService(
        change_applier_factory=FakeApplier,
        test_runner=runner,
    )

    validation_command = (
        "python -m pytest tests/unit/jobs/test_retry.py -xvs"
    )

    result = service.execute(
        tmp_path,
        make_implementation(),
        validation_command=validation_command,
    )

    assert result.status == ExecutionStatus.PASSED
    assert runner.received_workspace == tmp_path.resolve()
    assert runner.received_command == validation_command
