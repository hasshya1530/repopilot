from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agents.execution.errors import ExecutionValidationError
from agents.execution.models import ExecutionResult, ExecutionStatus
from agents.implementer.applier.models import ChangeApplicationResult
from agents.implementer.applier.service import ChangeApplier
from agents.implementer.models import ImplementationResult
from agents.testing.models import TestResult, TestStatus
from agents.testing.runner import TestRunner


class ChangeApplierProtocol(Protocol):
    def apply(self, implementation: ImplementationResult) -> ChangeApplicationResult:
        ...


class TestRunnerProtocol(Protocol):
    def run(self, repository_path: Path) -> TestResult:
        ...


class ChangeApplierFactoryProtocol(Protocol):
    def __call__(self, workspace_path: Path) -> ChangeApplierProtocol:
        ...


class ExecutionService:
    def __init__(
        self,
        change_applier_factory: ChangeApplierFactoryProtocol = ChangeApplier,
        test_runner: TestRunnerProtocol | None = None,
    ) -> None:
        self._change_applier_factory = change_applier_factory
        self._test_runner = test_runner or TestRunner()

    def execute(
        self,
        workspace_path: Path,
        implementation: ImplementationResult,
    ) -> ExecutionResult:
        workspace = workspace_path.resolve()

        if not workspace.exists():
            raise ExecutionValidationError(
                f"Workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise ExecutionValidationError(
                f"Workspace is not a directory: {workspace}"
            )

        applier = self._change_applier_factory(workspace)
        changes = applier.apply(implementation)
        tests = self._test_runner.run(workspace)

        if tests.status == TestStatus.PASSED:
            status = ExecutionStatus.PASSED
        else:
            status = ExecutionStatus.FAILED

        return ExecutionResult(
            status=status,
            changes=changes,
            tests=tests,
        )
