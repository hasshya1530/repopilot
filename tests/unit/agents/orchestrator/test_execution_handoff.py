from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from agents.approval.models import ApprovalResult
from agents.debugger.models import DebuggerStatus
from agents.execution.models import ExecutionStatus
from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from agents.orchestrator.models import OrchestrationStatus
from agents.orchestrator.protocols import OrchestrationDependencies
from agents.orchestrator.service import OrchestrationService
from agents.planner.models import PlanningContext
from agents.planner.plan_models import ImplementationPlan
from agents.reviewer.models import ReviewDecision, ReviewResult
from apps.api.app.models.pull_request import ApprovalStatus
from apps.api.app.models.task import TaskStatus
from ingestion.change_context.models import RepositoryChangeContext


class Persistence:
    def __init__(self, task: Any, repository: Any) -> None:
        self.task = task
        self.repository = repository
        self.statuses: list[TaskStatus] = []

    async def get_task(self, task_id):
        return self.task if task_id == self.task.id else None

    async def update_task_status(self, task_id, status):
        if task_id != self.task.id:
            return None
        self.task.status = status
        self.statuses.append(status)
        return self.task

    async def get_repository(self, repository_id):
        return self.repository if repository_id == self.repository.id else None


class PlanningContextBuilder:
    async def build(self, *args, **kwargs):
        repository_id = args[0]

        return PlanningContext(
            repository_id=repository_id,
            task_description="Update service.",
            files=(),
            symbols=(),
            dependencies=(),
            constraints=(),
            change_context=RepositoryChangeContext(
                repository_id=repository_id,
                task_description="Update service.",
                files=(),
                symbols=(),
                dependencies=(),
            ),
        )


class ImplementationContextBuilder:
    def build(self, **kwargs):
        return ImplementationContext(
            repository_id=kwargs["repository_id"],
            task_description=kwargs["task_description"],
            files=(),
            symbols=(),
            dependencies=(),
        )


class Planner:
    async def generate_plan(self, *args, **kwargs):
        return ImplementationPlan(
            summary="Update service.",
            assumptions=(),
            files_to_modify=(),
            files_to_create=(),
            symbols_to_modify=(),
            implementation_steps=(),
            dependencies=(),
            tests_to_add=(),
            validation_commands=(),
            risks=(),
        )


class Implementer:
    def __init__(self, implementation: ImplementationResult) -> None:
        self.implementation = implementation
        self.calls = 0

    async def implement(self, *args, **kwargs):
        self.calls += 1
        return self.implementation


class RecordingExecution:
    def __init__(self, succeeded: bool = True) -> None:
        self.succeeded = succeeded
        self.calls = 0
        self.workspace_path: Path | None = None
        self.implementation: ImplementationResult | None = None

    def execute(
        self,
        workspace_path: Path,
        implementation: ImplementationResult,
    ):
        self.calls += 1
        self.workspace_path = workspace_path
        self.implementation = implementation

        return SimpleNamespace(
            status=(
                ExecutionStatus.PASSED
                if self.succeeded
                else ExecutionStatus.FAILED
            ),
            succeeded=self.succeeded,
        )


class Debugger:
    def __init__(self, succeeded: bool = True) -> None:
        self.succeeded = succeeded
        self.calls = 0
        self.workspace_path: Path | None = None
        self.context: ImplementationContext | None = None

    async def debug(
        self,
        workspace_path: Path,
        context: ImplementationContext,
        *,
        task_id: UUID | None = None,
    ):
        self.calls += 1
        self.workspace_path = workspace_path
        self.context = context

        return SimpleNamespace(
            status=(
                DebuggerStatus.FIXED
                if self.succeeded
                else DebuggerStatus.LIMIT_REACHED
            ),
            attempts=(),
            final_test_result=SimpleNamespace(
                status=SimpleNamespace(
                    value="passed" if self.succeeded else "failed"
                )
            ),
            succeeded=self.succeeded,
        )


class Reviewer:
    async def review(self, **kwargs):
        return ReviewResult(
            decision=ReviewDecision.APPROVE,
            summary="Review completed.",
            findings=(),
        )


class Workspace:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.created = 0
        self.removed: list[Path] = []

    def create_from_repository(
        self,
        repository_path: Path,
        *,
        branch_name: str | None = None,
    ) -> Path:
        self.created += 1
        self.path.mkdir(parents=True, exist_ok=True)
        return self.path

    def info(self, workspace_path: Path):
        return SimpleNamespace(
            path=workspace_path,
            branch_name="repopilot/test",
            commit_sha="abc123",
            is_clean=True,
        )

    def remove(self, workspace_path: Path) -> None:
        self.removed.append(workspace_path)


class RepositorySource:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def prepare(self, repository):
        return self.path


class PullRequest:
    def __init__(self) -> None:
        self.calls = 0
        self.last_implementation: ImplementationResult | None = None
        self.pull_request_id = SimpleNamespace()

    async def create_pull_request_from_implementation(self, **kwargs):
        self.calls += 1
        self.last_implementation = kwargs["implementation"]

        return SimpleNamespace(id=self.pull_request_id)


class Approval:
    async def get_status(self, request):
        return ApprovalResult(
            pull_request_id=request.pull_request_id,
            status=ApprovalStatus.APPROVED,
        )

    async def require_approval(self, pull_request_id):
        return ApprovalResult(
            pull_request_id=pull_request_id,
            status=ApprovalStatus.APPROVED,
        )


def make_task() -> Any:
    from uuid import uuid4

    return SimpleNamespace(
        id=uuid4(),
        repository_id=uuid4(),
        title="Update service",
        description="Update service.",
        status=TaskStatus.PENDING,
        branch_name=None,
    )


def make_repository(task: Any) -> Any:
    return SimpleNamespace(
        id=task.repository_id,
        full_name="example/repository",
        clone_url="file:///tmp/repository",
        default_branch="main",
    )


def make_implementation() -> ImplementationResult:
    return ImplementationResult(
        summary="Updated service.",
        changes=(
            CodeChange(
                file_path="src/service.py",
                operation=ChangeOperation.MODIFY,
                content="def service():\n    return 2\n",
                reason="Update service behavior.",
            ),
        ),
    )


def make_dependencies(
    task: Any,
    repository: Any,
    implementation: ImplementationResult,
    execution: RecordingExecution,
    debugger: Debugger,
    workspace: Workspace,
    repository_source: RepositorySource,
) -> OrchestrationDependencies:
    return OrchestrationDependencies(
        persistence=Persistence(task, repository),
        repository_source=repository_source,
        planning_context_builder=PlanningContextBuilder(),
        planner=Planner(),
        implementation_context_builder=ImplementationContextBuilder(),
        implementer=Implementer(implementation),
        workspace=workspace,
        execution=execution,
        debugger=debugger,
        reviewer=Reviewer(),
        approval=Approval(),
        pull_request=PullRequest(),
    )


@pytest.mark.asyncio
async def test_orchestrator_passes_generated_implementation_to_execution(
    tmp_path: Path,
) -> None:
    task = make_task()
    repository = make_repository(task)
    implementation = make_implementation()

    execution = RecordingExecution(succeeded=True)
    debugger = Debugger(succeeded=True)
    workspace = Workspace(tmp_path / "workspace")
    repository_source = RepositorySource(tmp_path / "repository")

    dependencies = make_dependencies(
        task,
        repository,
        implementation,
        execution,
        debugger,
        workspace,
        repository_source,
    )

    result = await OrchestrationService(dependencies).run(task.id)

    assert result.status == OrchestrationStatus.WAITING_APPROVAL

    assert execution.calls == 1
    assert execution.workspace_path == workspace.path
    assert execution.implementation is implementation

    assert debugger.calls == 0
    assert workspace.created == 1
    assert workspace.removed == [workspace.path]


@pytest.mark.asyncio
async def test_orchestrator_sends_same_implementation_to_execution_and_pr(
    tmp_path: Path,
) -> None:
    task = make_task()
    repository = make_repository(task)
    implementation = make_implementation()

    execution = RecordingExecution(succeeded=True)
    debugger = Debugger(succeeded=True)
    workspace = Workspace(tmp_path / "workspace")
    repository_source = RepositorySource(tmp_path / "repository")

    dependencies = make_dependencies(
        task,
        repository,
        implementation,
        execution,
        debugger,
        workspace,
        repository_source,
    )

    result = await OrchestrationService(dependencies).run(task.id)

    assert result.status == OrchestrationStatus.WAITING_APPROVAL

    pull_request = dependencies.pull_request

    assert execution.implementation is implementation
    assert pull_request.last_implementation is implementation


@pytest.mark.asyncio
async def test_orchestrator_routes_failed_execution_to_debugger(
    tmp_path: Path,
) -> None:
    task = make_task()
    repository = make_repository(task)
    implementation = make_implementation()

    execution = RecordingExecution(succeeded=False)
    debugger = Debugger(succeeded=True)
    workspace = Workspace(tmp_path / "workspace")
    repository_source = RepositorySource(tmp_path / "repository")

    dependencies = make_dependencies(
        task,
        repository,
        implementation,
        execution,
        debugger,
        workspace,
        repository_source,
    )

    result = await OrchestrationService(dependencies).run(task.id)

    assert result.status == OrchestrationStatus.WAITING_APPROVAL

    assert execution.calls == 1
    assert execution.implementation is implementation

    assert debugger.calls == 1
    assert debugger.workspace_path == workspace.path
    assert debugger.context is not None

    assert workspace.created == 1
    assert workspace.removed == [workspace.path]
