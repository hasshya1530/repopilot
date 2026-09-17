from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agents.debugger.analyzer import FailureAnalysis, FailureAnalyzer
from agents.debugger.models import DebuggerResult, DebuggerStatus, RepairAttempt
from agents.debugger.repair_models import RepairProposal
from agents.implementer.applier.models import ChangeApplicationResult
from agents.implementer.applier.service import ChangeApplier
from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult
from agents.testing.models import TestResult, TestStatus
from agents.testing.runner import TestRunner


class ChangeApplierProtocol(Protocol):
    def apply(
        self,
        implementation: ImplementationResult,
    ) -> ChangeApplicationResult:
        ...


class ChangeApplierFactoryProtocol(Protocol):
    def __call__(
        self,
        workspace_path: Path,
    ) -> ChangeApplierProtocol:
        ...


class TestRunnerProtocol(Protocol):
    def run(
        self,
        repository_path: Path,
    ) -> TestResult:
        ...


class RepairGeneratorProtocol(Protocol):
    async def generate(
        self,
        analysis: FailureAnalysis,
        context: ImplementationContext,
        *,
        max_tokens: int = 8192,
    ) -> RepairProposal:
        ...


class DebuggerService:
    """Run an iterative test, analyze, repair, and retest loop."""

    def __init__(
        self,
        *,
        analyzer: FailureAnalyzer | None = None,
        repair_generator: RepairGeneratorProtocol,
        change_applier_factory: ChangeApplierFactoryProtocol = ChangeApplier,
        test_runner: TestRunnerProtocol | None = None,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        self._analyzer = analyzer or FailureAnalyzer()
        self._repair_generator = repair_generator
        self._change_applier_factory = change_applier_factory
        self._test_runner = test_runner or TestRunner()
        self._max_attempts = max_attempts

    async def debug(
        self,
        workspace_path: Path,
        context: ImplementationContext,
    ) -> DebuggerResult:
        workspace = workspace_path.resolve()

        if not workspace.exists():
            raise ValueError(f"Workspace does not exist: {workspace}")

        if not workspace.is_dir():
            raise ValueError(f"Workspace is not a directory: {workspace}")

        attempts: list[RepairAttempt] = []

        test_result = self._test_runner.run(workspace)

        if test_result.status == TestStatus.PASSED:
            return DebuggerResult(
                status=DebuggerStatus.FIXED,
                attempts=(),
                final_test_result=test_result,
            )

        for attempt_number in range(1, self._max_attempts + 1):
            analysis = self._analyzer.analyze(test_result)

            proposal = await self._repair_generator.generate(
                analysis,
                context,
            )

            implementation = ImplementationResult(
                summary=proposal.diagnosis,
                changes=proposal.changes,
            )

            applier = self._change_applier_factory(workspace)
            applier.apply(implementation)

            test_result = self._test_runner.run(workspace)

            attempts.append(
                RepairAttempt(
                    attempt=attempt_number,
                    diagnosis=proposal.diagnosis,
                    changes=proposal.changes,
                    test_result=test_result,
                )
            )

            if test_result.status == TestStatus.PASSED:
                return DebuggerResult(
                    status=DebuggerStatus.FIXED,
                    attempts=tuple(attempts),
                    final_test_result=test_result,
                )

        return DebuggerResult(
            status=DebuggerStatus.LIMIT_REACHED,
            attempts=tuple(attempts),
            final_test_result=test_result,
        )
