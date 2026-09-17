from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from agents.debugger.analyzer import FailureAnalysis
from agents.debugger.models import DebuggerStatus
from agents.debugger.repair_models import RepairProposal
from agents.debugger.service import DebuggerService
from agents.implementer.applier.models import (
    AppliedChange,
    AppliedChangeStatus,
    ChangeApplicationResult,
)
from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from agents.testing import models as testing_models


def make_context() -> ImplementationContext:
    return ImplementationContext(
        repository_id=UUID("00000000-0000-0000-0000-000000000001"),
        task_description="Fix the failing implementation.",
        files=(),
        symbols=(),
        dependencies=(),
    )


def make_test_result(
    status: testing_models.TestStatus,
    exit_code: int,
) -> testing_models.TestResult:
    return testing_models.TestResult(
        status=status,
        command=("pytest", "-q"),
        exit_code=exit_code,
        stdout="1 passed\n"
        if status == testing_models.TestStatus.PASSED
        else "",
        stderr="",
        duration_seconds=0.1,
    )


def make_proposal() -> RepairProposal:
    return RepairProposal(
        diagnosis="Fix the failing implementation.",
        changes=(
            CodeChange(
                file_path="example.py",
                operation=ChangeOperation.MODIFY,
                content="print('fixed')\n",
                reason="Fix the failing implementation.",
            ),
        ),
    )


class FakeTestRunner:
    def __init__(
        self,
        results: list[testing_models.TestResult],
    ) -> None:
        self.results = results
        self.calls = 0

    def run(self, repository_path: Path) -> testing_models.TestResult:
        result = self.results[self.calls]
        self.calls += 1
        return result


class FakeApplier:
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self.calls: list[ImplementationResult] = []

    def apply(
        self,
        implementation: ImplementationResult,
    ) -> ChangeApplicationResult:
        self.calls.append(implementation)

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


class FakeApplierFactory:
    def __init__(self) -> None:
        self.instances: list[FakeApplier] = []

    def __call__(self, workspace_path: Path) -> FakeApplier:
        applier = FakeApplier(workspace_path)
        self.instances.append(applier)
        return applier


def make_analyzer() -> Mock:
    analyzer = Mock()
    analyzer.analyze.return_value = FailureAnalysis(
        failure_type="assertion_error",
        summary="Tests failed.",
        details="AssertionError",
        test_command=("pytest", "-q"),
    )
    return analyzer


@pytest.mark.asyncio
async def test_debug_returns_fixed_when_tests_already_pass(
    tmp_path: Path,
) -> None:
    runner = FakeTestRunner(
        [
            make_test_result(
                testing_models.TestStatus.PASSED,
                0,
            ),
        ]
    )

    generator = AsyncMock()
    factory = FakeApplierFactory()
    analyzer = make_analyzer()

    service = DebuggerService(
        analyzer=analyzer,
        repair_generator=generator,
        change_applier_factory=factory,
        test_runner=runner,
    )

    result = await service.debug(
        tmp_path,
        make_context(),
    )

    assert result.status == DebuggerStatus.FIXED
    assert result.succeeded is True
    assert result.attempts == ()
    assert result.final_test_result.status == testing_models.TestStatus.PASSED
    assert runner.calls == 1
    generator.generate.assert_not_awaited()
    analyzer.analyze.assert_not_called()
    assert factory.instances == []


@pytest.mark.asyncio
async def test_debug_repairs_failure_and_passes(
    tmp_path: Path,
) -> None:
    runner = FakeTestRunner(
        [
            make_test_result(
                testing_models.TestStatus.FAILED,
                1,
            ),
            make_test_result(
                testing_models.TestStatus.PASSED,
                0,
            ),
        ]
    )

    generator = AsyncMock()
    generator.generate.return_value = make_proposal()

    factory = FakeApplierFactory()
    analyzer = make_analyzer()

    service = DebuggerService(
        analyzer=analyzer,
        repair_generator=generator,
        change_applier_factory=factory,
        test_runner=runner,
    )

    result = await service.debug(
        tmp_path,
        make_context(),
    )

    assert result.status == DebuggerStatus.FIXED
    assert result.succeeded is True
    assert len(result.attempts) == 1
    assert result.attempts[0].attempt == 1
    assert result.attempts[0].diagnosis == "Fix the failing implementation."
    assert result.attempts[0].test_result.status == testing_models.TestStatus.PASSED

    analyzer.analyze.assert_called_once()
    generator.generate.assert_awaited_once()

    assert len(factory.instances) == 1
    assert len(factory.instances[0].calls) == 1
    assert runner.calls == 2


@pytest.mark.asyncio
async def test_debug_retries_until_max_attempts(
    tmp_path: Path,
) -> None:
    runner = FakeTestRunner(
        [
            make_test_result(
                testing_models.TestStatus.FAILED,
                1,
            ),
            make_test_result(
                testing_models.TestStatus.FAILED,
                1,
            ),
            make_test_result(
                testing_models.TestStatus.FAILED,
                1,
            ),
            make_test_result(
                testing_models.TestStatus.FAILED,
                1,
            ),
        ]
    )

    generator = AsyncMock()
    generator.generate.return_value = make_proposal()

    factory = FakeApplierFactory()
    analyzer = make_analyzer()

    service = DebuggerService(
        analyzer=analyzer,
        repair_generator=generator,
        change_applier_factory=factory,
        test_runner=runner,
        max_attempts=3,
    )

    result = await service.debug(
        tmp_path,
        make_context(),
    )

    assert result.status == DebuggerStatus.LIMIT_REACHED
    assert result.succeeded is False
    assert len(result.attempts) == 3
    assert runner.calls == 4
    assert analyzer.analyze.call_count == 3
    assert generator.generate.await_count == 3
    assert len(factory.instances) == 3


@pytest.mark.asyncio
async def test_debug_rejects_invalid_max_attempts(
    tmp_path: Path,
) -> None:
    generator = AsyncMock()

    with pytest.raises(
        ValueError,
        match="max_attempts must be at least 1",
    ):
        DebuggerService(
            repair_generator=generator,
            max_attempts=0,
        )


@pytest.mark.asyncio
async def test_debug_rejects_missing_workspace(
    tmp_path: Path,
) -> None:
    generator = AsyncMock()

    service = DebuggerService(
        repair_generator=generator,
    )

    missing_workspace = tmp_path / "missing"

    with pytest.raises(
        ValueError,
        match="Workspace does not exist",
    ):
        await service.debug(
            missing_workspace,
            make_context(),
        )
