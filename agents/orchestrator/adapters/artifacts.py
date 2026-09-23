from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.debugger.service import DebuggerArtifactPersistenceProtocol
from agents.execution.models import ExecutionResult
from agents.implementer.applier.models import ChangeApplicationResult
from agents.implementer.models import ImplementationResult
from agents.orchestrator.protocols import ArtifactPersistenceProtocol
from agents.testing.models import TestResult
from apps.api.app.models.agent_run import AgentRun
from apps.api.app.models.file_change import FileChange
from apps.api.app.models.task_step import AgentType, TaskStep
from apps.api.app.models.test_run import TestRun
from apps.api.app.services.artifacts import (
    complete_agent_run,
    complete_task_step,
    create_agent_run,
    create_task_step,
    fail_agent_run,
    fail_task_step,
)
from apps.api.app.services.implementation_artifacts import (
    FileSnapshot,
    capture_implementation_snapshots,
    persist_applied_changes,
)
from apps.api.app.services.test_artifacts import persist_test_result


class SqlAlchemyArtifactPersistence(
    ArtifactPersistenceProtocol,
    DebuggerArtifactPersistenceProtocol,
):
    """SQLAlchemy-backed persistence for orchestration execution artifacts."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        model_provider: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self._session = session
        self._model_provider = model_provider
        self._model_name = model_name

    async def start_agent(
        self,
        *,
        task_id: UUID,
        agent_type: AgentType,
        step_number: int,
        step_name: str,
        input_data: str | None = None,
        model_provider: str | None = None,
        model_name: str | None = None,
        attempt_number: int = 1,
    ) -> tuple[TaskStep, AgentRun]:
        step = await create_task_step(
            self._session,
            task_id=task_id,
            step_number=step_number,
            name=step_name,
            agent_type=agent_type,
            input_data=input_data,
        )

        run = await create_agent_run(
            self._session,
            task_step_id=step.id,
            agent_type=agent_type,
            attempt_number=attempt_number,
            model_provider=model_provider or self._model_provider,
            model_name=model_name or self._model_name,
            input_data=input_data,
        )

        return step, run

    async def complete_agent(
        self,
        *,
        task_step_id: UUID,
        agent_run_id: UUID,
        output_data: str | None = None,
    ) -> tuple[TaskStep | None, AgentRun | None]:
        run = await complete_agent_run(
            self._session,
            agent_run_id,
            output_data=output_data,
        )
        step = await complete_task_step(
            self._session,
            task_step_id,
            output_data=output_data,
        )
        return step, run

    async def fail_agent(
        self,
        *,
        task_step_id: UUID,
        agent_run_id: UUID,
        error_message: str,
    ) -> tuple[TaskStep | None, AgentRun | None]:
        run = await fail_agent_run(
            self._session,
            agent_run_id,
            error_message=error_message,
        )
        step = await fail_task_step(
            self._session,
            task_step_id,
            error_message=error_message,
        )
        return step, run

    def capture_snapshots(
        self,
        *,
        workspace_path: Path,
        implementation: ImplementationResult,
    ) -> dict[str, FileSnapshot]:
        return capture_implementation_snapshots(
            workspace_path,
            implementation,
        )

    async def persist_implementation(
        self,
        *,
        agent_run_id: UUID,
        workspace_path: Path,
        implementation: ImplementationResult,
        application_result: ChangeApplicationResult,
        snapshots: dict[str, FileSnapshot],
    ) -> list[FileChange]:
        return await persist_applied_changes(
            self._session,
            agent_run_id=agent_run_id,
            implementation=implementation,
            application_result=application_result,
            snapshots=snapshots,
            workspace_path=workspace_path,
        )

    async def persist_test_result(
        self,
        *,
        agent_run_id: UUID,
        workspace_path: Path,
        execution: ExecutionResult,
    ) -> TestRun:
        return await persist_test_result(
            self._session,
            agent_run_id=agent_run_id,
            result=execution.tests,
            working_directory=workspace_path,
        )

    # ---------------------------------------------------------------
    # Debugger persistence
    # ---------------------------------------------------------------

    async def start(
        self,
        *,
        task_id: UUID,
        input_data: str | None,
        attempt_number: int,
    ) -> tuple[UUID, UUID]:
        step, run = await self.start_agent(
            task_id=task_id,
            agent_type=AgentType.DEBUGGER,
            step_number=5,
            step_name="debugging",
            input_data=input_data,
            attempt_number=attempt_number,
        )
        return step.id, run.id

    async def persist_test(
        self,
        *,
        agent_run_id: UUID,
        workspace_path: Path,
        test_result: TestResult,
    ) -> None:
        await persist_test_result(
            self._session,
            agent_run_id=agent_run_id,
            result=test_result,
            working_directory=workspace_path,
        )

    async def persist_changes(
        self,
        *,
        agent_run_id: UUID,
        workspace_path: Path,
        implementation: ImplementationResult,
        application_result: ChangeApplicationResult,
        snapshots: dict[str, FileSnapshot],
    ) -> None:
        await persist_applied_changes(
            self._session,
            agent_run_id=agent_run_id,
            implementation=implementation,
            application_result=application_result,
            snapshots=snapshots,
            workspace_path=workspace_path,
        )

    async def complete(
        self,
        *,
        task_step_id: UUID,
        agent_run_id: UUID,
        output_data: str | None,
    ) -> None:
        await self.complete_agent(
            task_step_id=task_step_id,
            agent_run_id=agent_run_id,
            output_data=output_data,
        )

    async def fail(
        self,
        *,
        task_step_id: UUID,
        agent_run_id: UUID,
        error_message: str,
    ) -> None:
        await self.fail_agent(
            task_step_id=task_step_id,
            agent_run_id=agent_run_id,
            error_message=error_message,
        )


def serialize_implementation(
    implementation: ImplementationResult,
) -> str:
    return json.dumps(
        {
            "summary": implementation.summary,
            "changes": [
                {
                    "file_path": change.file_path,
                    "operation": change.operation.value,
                    "content": change.content,
                    "reason": change.reason,
                }
                for change in implementation.changes
            ],
        },
        sort_keys=True,
    )
