from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from agents.approval.models import ApprovalResult
from agents.debugger.models import DebuggerResult, DebuggerStatus
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


class FakePersistence:
    def __init__(self, task: Any, repository: Any) -> None:
        self.task = task
        self.repository = repository
        self.statuses: list[TaskStatus] = []

    async def get_task(self, task_id: UUID) -> Any:
        return self.task if task_id == self.task.id else None

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
    ) -> Any:
        if task_id != self.task.id:
            return None

        self.task.status = status
        self.statuses.append(status)
        return self.task

    async def get_repository(self, repository_id: UUID) -> Any:
        return (
            self.repository
            if repository_id == self.repository.id
            else None
        )


class FakePlanningContextBuilder:
    def __init__(self, context: PlanningContext) -> None:
        self.context = context
        self.calls = 0

    async def build(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> PlanningContext:
        self.calls += 1
        return self.context


class FakeImplementationContextBuilder:
    def __init__(self, context: ImplementationContext) -> None:
        self.context = context
        self.calls = 0
        self.last_kwargs: dict[str, Any] = {}

    def build(
        self,
        **kwargs: Any,
    ) -> ImplementationContext:
        self.calls += 1
        self.last_kwargs = kwargs
        return self.context


class FakePlanner:
    def __init__(self, plan: ImplementationPlan) -> None:
        self.result = plan
        self.calls = 0

    async def plan(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ImplementationPlan:
        self.calls += 1
        return self.result


class FakeImplementer:
    def __init__(
        self,
        result: ImplementationResult,
    ) -> None:
        self.result = result
        self.calls = 0

    async def implement(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ImplementationResult:
        self.calls += 1
        return self.result


class FakeExecution:
    def __init__(self, succeeded: bool) -> None:
        self.succeeded = succeeded
        self.calls = 0

    def execute(
        self,
        workspace_path: Path,
        implementation: ImplementationResult,
    ) -> Any:
        self.calls += 1

        return SimpleNamespace(
            status=(
                ExecutionStatus.PASSED
                if self.succeeded
                else ExecutionStatus.FAILED
            ),
            succeeded=self.succeeded,
        )


class FakeDebugger:
    def __init__(self, succeeded: bool) -> None:
        self.succeeded = succeeded
        self.calls = 0

    async def debug(
        self,
        workspace_path: Path,
        context: ImplementationContext,
        *,
        task_id: UUID | None = None,
    ) -> DebuggerResult:
        self.calls += 1

        return SimpleNamespace(
            status=(
                DebuggerStatus.FIXED
                if self.succeeded
                else DebuggerStatus.LIMIT_REACHED
            ),
            attempts=(),
            final_test_result=SimpleNamespace(
                status=SimpleNamespace(
                    value="passed"
                    if self.succeeded
                    else "failed"
                )
            ),
            succeeded=self.succeeded,
        )


class FakeReviewer:
    def __init__(
        self,
        decision: ReviewDecision,
    ) -> None:
        self.decision = decision
        self.calls = 0
        self.last_context: ImplementationContext | None = None
        self.last_implementation: ImplementationResult | None = None

    async def review(
        self,
        **kwargs: Any,
    ) -> ReviewResult:
        self.calls += 1
        self.last_context = kwargs["context"]
        self.last_implementation = kwargs["implementation"]

        return ReviewResult(
            decision=self.decision,
            summary="Review completed.",
            findings=(),
        )


class FakeWorkspace:
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
        return self.path

    def info(self, workspace_path: Path) -> Any:
        return SimpleNamespace(
            path=workspace_path,
            branch_name="repopilot/test",
            commit_sha="abc123",
            is_clean=True,
        )

    def remove(self, workspace_path: Path) -> None:
        self.removed.append(workspace_path)


class FakeRepositorySource:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.calls = 0

    async def prepare(self, repository: Any) -> Path:
        self.calls += 1
        return self.path


class FakePullRequestService:
    def __init__(self) -> None:
        self.calls = 0
        self.last_implementation: ImplementationResult | None = None
        self.pull_request_id = uuid4()

    async def create_pull_request_from_implementation(
        self,
        **kwargs: Any,
    ) -> Any:
        self.calls += 1
        self.last_implementation = kwargs["implementation"]

        return SimpleNamespace(
            id=self.pull_request_id,
        )


class FakeApproval:
    def __init__(
        self,
        status: ApprovalStatus,
    ) -> None:
        self.status = status
        self.status_calls = 0

    async def get_status(
        self,
        request: Any,
    ) -> ApprovalResult:
        self.status_calls += 1

        return ApprovalResult(
            pull_request_id=request.pull_request_id,
            status=self.status,
        )

    async def require_approval(
        self,
        pull_request_id: UUID,
    ) -> ApprovalResult:
        return ApprovalResult(
            pull_request_id=pull_request_id,
            status=self.status,
        )


def make_task() -> Any:
    return SimpleNamespace(
        id=uuid4(),
        repository_id=uuid4(),
        title="Fix authentication",
        description="Fix authentication.",
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


def make_change_context(
    repository_id: UUID,
) -> RepositoryChangeContext:
    return RepositoryChangeContext(
        repository_id=repository_id,
        task_description="Fix authentication.",
        files=(),
        symbols=(),
        dependencies=(),
    )


def make_planning_context(
    repository_id: UUID,
) -> PlanningContext:
    change_context = make_change_context(repository_id)

    return PlanningContext(
        repository_id=repository_id,
        task_description="Fix authentication.",
        files=(),
        symbols=(),
        dependencies=(),
        constraints=(),
        change_context=change_context,
    )


def make_implementation_context(
    repository_id: UUID,
) -> ImplementationContext:
    return ImplementationContext(
        repository_id=repository_id,
        task_description="Fix authentication.",
        files=(),
        symbols=(),
        dependencies=(),
    )


def make_plan() -> ImplementationPlan:
    return ImplementationPlan(
        summary="Fix authentication.",
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


def make_implementation() -> ImplementationResult:
    return ImplementationResult(
        summary="Authentication fixed.",
        changes=(
            CodeChange(
                file_path="auth.py",
                operation=ChangeOperation.MODIFY,
                content="print('fixed')",
                reason="Fix authentication.",
            ),
        ),
    )


def make_dependencies(
    task: Any,
    repository: Any,
    *,
    execution_succeeded: bool,
    debugger_succeeded: bool = True,
    review_decision: ReviewDecision = ReviewDecision.APPROVE,
) -> tuple[
    OrchestrationDependencies,
    FakePersistence,
    FakeExecution,
    FakeDebugger,
    FakeReviewer,
    FakeWorkspace,
    FakeRepositorySource,
    FakePullRequestService,
]:
    planning_context = make_planning_context(repository.id)
    implementation_context = make_implementation_context(repository.id)

    persistence = FakePersistence(task, repository)
    execution = FakeExecution(execution_succeeded)
    debugger = FakeDebugger(debugger_succeeded)
    reviewer = FakeReviewer(review_decision)
    workspace = FakeWorkspace(
        Path("/tmp/repopilot-test")
    )
    repository_source = FakeRepositorySource(
        Path("/tmp/source-repository")
    )
    pull_request = FakePullRequestService()

    dependencies = OrchestrationDependencies(
        planning_context_builder=FakePlanningContextBuilder(
            planning_context
        ),
        implementation_context_builder=FakeImplementationContextBuilder(
            implementation_context
        ),
        planner=FakePlanner(make_plan()),
        implementer=FakeImplementer(
            make_implementation()
        ),
        execution=execution,
        debugger=debugger,
        reviewer=reviewer,
        approval=FakeApproval(
            ApprovalStatus.APPROVED
        ),
        pull_request=pull_request,
        workspace=workspace,
        repository_source=repository_source,
        persistence=persistence,
    )

    return (
        dependencies,
        persistence,
        execution,
        debugger,
        reviewer,
        workspace,
        repository_source,
        pull_request,
    )


@pytest.mark.asyncio
async def test_run_reaches_waiting_approval() -> None:
    task = make_task()
    repository = make_repository(task)

    (
        dependencies,
        persistence,
        execution,
        debugger,
        reviewer,
        workspace,
        repository_source,
        pull_request,
    ) = make_dependencies(
        task,
        repository,
        execution_succeeded=True,
    )

    service = OrchestrationService(dependencies)

    result = await service.run(task.id)

    assert result.status == OrchestrationStatus.WAITING_APPROVAL
    assert result.pull_request_id == pull_request.pull_request_id
    assert result.error is None

    assert persistence.statuses == [
        TaskStatus.PLANNING,
        TaskStatus.IMPLEMENTING,
        TaskStatus.TESTING,
        TaskStatus.REVIEWING,
        TaskStatus.WAITING_APPROVAL,
    ]

    assert execution.calls == 1
    assert debugger.calls == 0
    assert reviewer.calls == 1
    assert pull_request.calls == 1
    assert repository_source.calls == 1
    assert workspace.created == 1
    assert workspace.removed == [workspace.path]


@pytest.mark.asyncio
async def test_run_fails_without_changes() -> None:
    task = make_task()
    repository = make_repository(task)

    dependencies, persistence, _, _, _, workspace, _, pull_request = (
        make_dependencies(
            task,
            repository,
            execution_succeeded=True,
        )
    )

    class NoChangeImplementer:
        async def implement(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> ImplementationResult:
            return ImplementationResult(
                summary="No changes.",
                changes=(),
            )

    dependencies.implementer = NoChangeImplementer()

    service = OrchestrationService(dependencies)

    result = await service.run(task.id)

    assert result.status == OrchestrationStatus.FAILED
    assert result.error == "Implementation produced no changes."
    assert persistence.statuses == [
        TaskStatus.PLANNING,
        TaskStatus.IMPLEMENTING,
        TaskStatus.FAILED,
    ]
    assert workspace.created == 0
    assert workspace.removed == []
    assert pull_request.calls == 0


@pytest.mark.asyncio
async def test_run_enters_debugging_when_execution_fails() -> None:
    task = make_task()
    repository = make_repository(task)

    (
        dependencies,
        persistence,
        execution,
        debugger,
        reviewer,
        workspace,
        repository_source,
        pull_request,
    ) = make_dependencies(
        task,
        repository,
        execution_succeeded=False,
        debugger_succeeded=True,
    )

    service = OrchestrationService(dependencies)

    result = await service.run(task.id)

    assert result.status == OrchestrationStatus.WAITING_APPROVAL
    assert persistence.statuses == [
        TaskStatus.PLANNING,
        TaskStatus.IMPLEMENTING,
        TaskStatus.TESTING,
        TaskStatus.REVIEWING,
        TaskStatus.WAITING_APPROVAL,
    ]
    assert execution.calls == 1
    assert debugger.calls == 1
    assert reviewer.calls == 1
    assert repository_source.calls == 1
    assert workspace.created == 1
    assert workspace.removed == [workspace.path]
    assert pull_request.calls == 1


@pytest.mark.asyncio
async def test_run_fails_when_debugger_cannot_fix() -> None:
    task = make_task()
    repository = make_repository(task)

    (
        dependencies,
        persistence,
        execution,
        debugger,
        reviewer,
        workspace,
        repository_source,
        pull_request,
    ) = make_dependencies(
        task,
        repository,
        execution_succeeded=False,
        debugger_succeeded=False,
    )

    service = OrchestrationService(dependencies)

    result = await service.run(task.id)

    assert result.status == OrchestrationStatus.FAILED
    assert (
        result.error
        == "Automated debugging could not produce "
        "a passing test result."
    )
    assert persistence.statuses == [
        TaskStatus.PLANNING,
        TaskStatus.IMPLEMENTING,
        TaskStatus.TESTING,
        TaskStatus.FAILED,
    ]
    assert execution.calls == 1
    assert debugger.calls == 1
    assert reviewer.calls == 0
    assert repository_source.calls == 1
    assert workspace.created == 1
    assert workspace.removed == [workspace.path]
    assert pull_request.calls == 0


@pytest.mark.asyncio
async def test_run_fails_when_review_requests_changes() -> None:
    task = make_task()
    repository = make_repository(task)

    (
        dependencies,
        persistence,
        execution,
        debugger,
        reviewer,
        workspace,
        repository_source,
        pull_request,
    ) = make_dependencies(
        task,
        repository,
        execution_succeeded=True,
        review_decision=ReviewDecision.REQUEST_CHANGES,
    )

    service = OrchestrationService(dependencies)

    result = await service.run(task.id)

    assert result.status == OrchestrationStatus.FAILED
    assert result.error == "Code review requested changes."
    assert persistence.statuses == [
        TaskStatus.PLANNING,
        TaskStatus.IMPLEMENTING,
        TaskStatus.TESTING,
        TaskStatus.REVIEWING,
        TaskStatus.FAILED,
    ]
    assert execution.calls == 1
    assert debugger.calls == 0
    assert reviewer.calls == 1
    assert repository_source.calls == 1
    assert workspace.created == 1
    assert workspace.removed == [workspace.path]
    assert pull_request.calls == 0


@pytest.mark.asyncio
async def test_run_rejects_non_pending_task() -> None:
    task = make_task()
    task.status = TaskStatus.WAITING_APPROVAL
    repository = make_repository(task)

    dependencies, *_ = make_dependencies(
        task,
        repository,
        execution_succeeded=True,
    )

    service = OrchestrationService(dependencies)

    with pytest.raises(Exception, match="cannot start"):
        await service.run(task.id)


@pytest.mark.asyncio
async def test_run_rejects_missing_task() -> None:
    task = make_task()
    repository = make_repository(task)

    dependencies, persistence, *_ = make_dependencies(
        task,
        repository,
        execution_succeeded=True,
    )

    missing_task_id = uuid4()

    with pytest.raises(Exception, match="was not found"):
        await OrchestrationService(dependencies).run(missing_task_id)

    assert persistence.statuses == []


@pytest.mark.asyncio
async def test_resume_approval_completes_task() -> None:
    task = make_task()
    task.status = TaskStatus.WAITING_APPROVAL
    repository = make_repository(task)

    dependencies, persistence, *_ = make_dependencies(
        task,
        repository,
        execution_succeeded=True,
    )

    service = OrchestrationService(dependencies)

    pull_request_id = uuid4()

    result = await service.resume_approval(
        task.id,
        pull_request_id,
    )

    assert result.status == OrchestrationStatus.COMPLETED
    assert result.pull_request_id == pull_request_id
    assert result.error is None
    assert result.metadata["approval_status"] == ApprovalStatus.APPROVED.value
    assert persistence.statuses == [TaskStatus.COMPLETED]


@pytest.mark.asyncio
async def test_resume_approval_stays_waiting_when_pending() -> None:
    task = make_task()
    task.status = TaskStatus.WAITING_APPROVAL
    repository = make_repository(task)

    dependencies, persistence, *_ = make_dependencies(
        task,
        repository,
        execution_succeeded=True,
    )

    dependencies.approval = FakeApproval(ApprovalStatus.PENDING)

    service = OrchestrationService(dependencies)

    pull_request_id = uuid4()

    result = await service.resume_approval(
        task.id,
        pull_request_id,
    )

    assert result.status == OrchestrationStatus.WAITING_APPROVAL
    assert result.pull_request_id == pull_request_id
    assert result.error is None
    assert result.metadata["approval_status"] == ApprovalStatus.PENDING.value
    assert persistence.statuses == []


@pytest.mark.asyncio
async def test_debugger_changes_are_forwarded_to_pull_request() -> None:
    task = make_task()
    repository = make_repository(task)

    (
        dependencies,
        _,
        _,
        _,
        _,
        _,
        _,
        pull_request,
    ) = make_dependencies(
        task,
        repository,
        execution_succeeded=False,
        debugger_succeeded=True,
    )

    original = make_implementation()

    class RepairingDebugger:
        async def debug(
            self,
            workspace_path: Path,
            context: ImplementationContext,
            *,
            task_id: UUID | None = None,
        ) -> DebuggerResult:
            return SimpleNamespace(
                status=DebuggerStatus.FIXED,
                attempts=(
                    SimpleNamespace(
                        changes=(
                            CodeChange(
                                file_path="auth.py",
                                operation=ChangeOperation.MODIFY,
                                content="print('repaired')",
                                reason="Fix failing test.",
                            ),
                        )
                    ),
                ),
                final_test_result=SimpleNamespace(
                    status=SimpleNamespace(value="passed")
                ),
                succeeded=True,
            )

    class OriginalImplementer:
        async def implement(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> ImplementationResult:
            return original

    dependencies.implementer = OriginalImplementer()
    dependencies.debugger = RepairingDebugger()

    result = await OrchestrationService(dependencies).run(task.id)

    assert result.status == OrchestrationStatus.WAITING_APPROVAL
    assert pull_request.last_implementation is not None
    assert len(pull_request.last_implementation.changes) == 1
    assert pull_request.last_implementation.changes[0].content == "print('repaired')"
