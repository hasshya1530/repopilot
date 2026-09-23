from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from agents.debugger.analyzer import FailureAnalysis, FailureAnalyzer
from agents.debugger.models import DebuggerResult, DebuggerStatus, RepairAttempt
from agents.debugger.repair_models import RepairProposal
from agents.debugger.validator import RepairValidator
from agents.implementer.applier.models import ChangeApplicationResult
from agents.implementer.applier.service import ChangeApplier
from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult
from agents.testing.models import TestResult, TestStatus
from agents.testing.runner import TestRunner
from apps.api.app.services.implementation_artifacts import FileSnapshot


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


class DebuggerArtifactPersistenceProtocol(Protocol):
    async def start(
        self,
        *,
        task_id: UUID,
        input_data: str | None,
        attempt_number: int,
    ) -> tuple[UUID, UUID]:
        ...

    async def persist_test(
        self,
        *,
        agent_run_id: UUID,
        workspace_path: Path,
        test_result: TestResult,
    ) -> None:
        ...

    def capture_snapshots(
        self,
        *,
        workspace_path: Path,
        implementation: ImplementationResult,
    ) -> dict[str, FileSnapshot]:
        ...

    async def persist_changes(
        self,
        *,
        agent_run_id: UUID,
        workspace_path: Path,
        implementation: ImplementationResult,
        application_result: ChangeApplicationResult,
        snapshots: dict[str, FileSnapshot],
    ) -> None:
        ...

    async def complete(
        self,
        *,
        task_step_id: UUID,
        agent_run_id: UUID,
        output_data: str | None,
    ) -> None:
        ...

    async def fail(
        self,
        *,
        task_step_id: UUID,
        agent_run_id: UUID,
        error_message: str,
    ) -> None:
        ...


class DebuggerService:
    """Run an iterative test, analyze, validate, repair, and retest loop."""

    def __init__(
        self,
        *,
        repair_generator: RepairGeneratorProtocol,
        analyzer: FailureAnalyzer | None = None,
        repair_validator: RepairValidator | None = None,
        change_applier_factory: ChangeApplierFactoryProtocol = ChangeApplier,
        test_runner: TestRunnerProtocol | None = None,
        max_attempts: int = 3,
        artifact_persistence: DebuggerArtifactPersistenceProtocol | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        self._analyzer = analyzer or FailureAnalyzer()
        self._repair_generator = repair_generator
        self._repair_validator = repair_validator or RepairValidator()
        self._change_applier_factory = change_applier_factory
        self._test_runner = test_runner or TestRunner()
        self._max_attempts = max_attempts
        self._artifact_persistence = artifact_persistence

    async def debug(
        self,
        workspace_path: Path,
        context: ImplementationContext,
        *,
        task_id: UUID | None = None,
    ) -> DebuggerResult:
        workspace = workspace_path.resolve()

        if not workspace.exists():
            raise ValueError(f"Workspace does not exist: {workspace}")

        if not workspace.is_dir():
            raise ValueError(f"Workspace is not a directory: {workspace}")

        attempts: list[RepairAttempt] = []

        persistence = self._artifact_persistence
        artifact_ids: tuple[UUID, UUID] | None = None

        if persistence is not None and task_id is not None:
            artifact_ids = await persistence.start(
                task_id=task_id,
                input_data=context.task_description,
                attempt_number=1,
            )

        test_result = self._test_runner.run(workspace)

        if persistence is not None and artifact_ids is not None:
            await persistence.persist_test(
                agent_run_id=artifact_ids[1],
                workspace_path=workspace,
                test_result=test_result,
            )

        if test_result.status == TestStatus.PASSED:
            result = DebuggerResult(
                status=DebuggerStatus.FIXED,
                attempts=(),
                final_test_result=test_result,
            )

            if persistence is not None and artifact_ids is not None:
                await persistence.complete(
                    task_step_id=artifact_ids[0],
                    agent_run_id=artifact_ids[1],
                    output_data="Debugger found no repair necessary.",
                )

            return result

        for attempt_number in range(1, self._max_attempts + 1):
            analysis = self._analyzer.analyze(test_result)

            proposal = await self._repair_generator.generate(
                analysis,
                context,
            )

            validation = self._repair_validator.validate(proposal)

            if not validation.valid:
                error_message = (
                    "Generated repair failed validation: "
                    + "; ".join(validation.errors)
                )

                if persistence is not None and artifact_ids is not None:
                    await persistence.fail(
                        task_step_id=artifact_ids[0],
                        agent_run_id=artifact_ids[1],
                        error_message=error_message,
                    )

                raise ValueError(error_message)

            implementation = ImplementationResult(
                summary=proposal.diagnosis,
                changes=proposal.changes,
            )

            snapshots: dict[str, FileSnapshot] | None = None

            if persistence is not None and artifact_ids is not None:
                snapshots = persistence.capture_snapshots(
                    workspace_path=workspace,
                    implementation=implementation,
                )

            applier = self._change_applier_factory(workspace)

            try:
                application_result = applier.apply(implementation)
            except Exception as exc:
                if persistence is not None and artifact_ids is not None:
                    await persistence.fail(
                        task_step_id=artifact_ids[0],
                        agent_run_id=artifact_ids[1],
                        error_message=str(exc),
                    )
                raise

            if (
                persistence is not None
                and artifact_ids is not None
                and snapshots is not None
            ):
                await persistence.persist_changes(
                    agent_run_id=artifact_ids[1],
                    workspace_path=workspace,
                    implementation=implementation,
                    application_result=application_result,
                    snapshots=snapshots,
                )

            test_result = self._test_runner.run(workspace)

            if persistence is not None and artifact_ids is not None:
                await persistence.persist_test(
                    agent_run_id=artifact_ids[1],
                    workspace_path=workspace,
                    test_result=test_result,
                )

            attempts.append(
                RepairAttempt(
                    attempt=attempt_number,
                    diagnosis=proposal.diagnosis,
                    changes=proposal.changes,
                    test_result=test_result,
                )
            )

            if test_result.status == TestStatus.PASSED:
                result = DebuggerResult(
                    status=DebuggerStatus.FIXED,
                    attempts=tuple(attempts),
                    final_test_result=test_result,
                )

                if persistence is not None and artifact_ids is not None:
                    await persistence.complete(
                        task_step_id=artifact_ids[0],
                        agent_run_id=artifact_ids[1],
                        output_data=(
                            f"Debugger fixed the failure after "
                            f"{attempt_number} repair attempt(s)."
                        ),
                    )

                return result

        result = DebuggerResult(
            status=DebuggerStatus.LIMIT_REACHED,
            attempts=tuple(attempts),
            final_test_result=test_result,
        )

        if persistence is not None and artifact_ids is not None:
            await persistence.fail(
                task_step_id=artifact_ids[0],
                agent_run_id=artifact_ids[1],
                error_message=(
                    f"Debugger reached the maximum of "
                    f"{self._max_attempts} repair attempts."
                ),
            )

        return result
