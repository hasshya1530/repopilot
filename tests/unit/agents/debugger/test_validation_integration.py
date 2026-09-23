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
from agents.testing.models import TestResult, TestStatus


def make_context() -> ImplementationContext:
    return ImplementationContext(
        repository_id=UUID("00000000-0000-0000-0000-000000000001"),
        task_description="Fix the failing implementation.",
        files=(),
        symbols=(),
        dependencies=(),
    )


def make_result(
    status: TestStatus,
    exit_code: int,
) -> TestResult:
    return TestResult(
        status=status,
        command=("pytest", "-q"),
        exit_code=exit_code,
        stdout="",
        stderr="AssertionError" if status == TestStatus.FAILED else "",
        duration_seconds=0.1,
    )


class RecordingRunner:
    def __init__(self) -> None:
        self.results = [
            make_result(TestStatus.FAILED, 1),
            make_result(TestStatus.PASSED, 0),
        ]
        self.calls = 0

    def run(self, workspace: Path) -> TestResult:
        result = self.results[self.calls]
        self.calls += 1
        return result


class RecordingApplier:
    def __init__(self, workspace: Path) -> None:
        self.calls: list[ImplementationResult] = []

    def apply(
        self,
        implementation: ImplementationResult,
    ) -> ChangeApplicationResult:
        self.calls.append(implementation)

        return ChangeApplicationResult(
            changes=tuple(
                AppliedChange(
                    file_path=change.file_path,
                    status=AppliedChangeStatus.APPLIED,
                    operation=change.operation.value,
                    diff="",
                )
                for change in implementation.changes
            ),
            files_changed=len(implementation.changes),
            dry_run=False,
        )


class RecordingApplierFactory:
    def __init__(self) -> None:
        self.instances: list[RecordingApplier] = []

    def __call__(self, workspace: Path) -> RecordingApplier:
        applier = RecordingApplier(workspace)
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
async def test_debug_validates_repair_before_application(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner()
    factory = RecordingApplierFactory()

    generator = AsyncMock()
    generator.generate.return_value = RepairProposal(
        diagnosis="Fix the failure.",
        changes=(
            CodeChange(
                file_path="../outside.py",
                operation=ChangeOperation.MODIFY,
                content="unsafe = True\n",
                reason="Unsafe repair.",
            ),
        ),
    )

    service = DebuggerService(
        analyzer=make_analyzer(),
        repair_generator=generator,
        change_applier_factory=factory,
        test_runner=runner,
    )

    with pytest.raises(
        ValueError,
        match="Generated repair failed validation",
    ):
        await service.debug(
            tmp_path,
            make_context(),
        )

    assert factory.instances == []
    assert runner.calls == 1


@pytest.mark.asyncio
async def test_debug_applies_validated_repair_and_retests(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner()
    factory = RecordingApplierFactory()

    generator = AsyncMock()
    generator.generate.return_value = RepairProposal(
        diagnosis="Fix the failure.",
        changes=(
            CodeChange(
                file_path="example.py",
                operation=ChangeOperation.MODIFY,
                content="print('fixed')\n",
                reason="Fix failing behavior.",
            ),
        ),
    )

    service = DebuggerService(
        analyzer=make_analyzer(),
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
    assert runner.calls == 2
    assert len(factory.instances) == 1
    assert len(factory.instances[0].calls) == 1
    assert (
        factory.instances[0].calls[0].changes[0].file_path
        == "example.py"
    )
