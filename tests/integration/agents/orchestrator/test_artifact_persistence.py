from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.approval.models import ApprovalRequest, ApprovalResult
from agents.execution.models import ExecutionResult, ExecutionStatus
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
from agents.orchestrator.adapters.artifacts import (
    SqlAlchemyArtifactPersistence,
)
from agents.orchestrator.protocols import OrchestrationDependencies
from agents.orchestrator.service import OrchestrationService
from agents.planner.models import PlanningContext
from agents.planner.plan_models import ImplementationPlan, PlannedFile
from agents.reviewer.models import ReviewDecision, ReviewResult
from agents.testing.models import TestResult, TestStatus
from agents.workspace.models import WorkspaceInfo
from apps.api.app.models.agent_run import AgentRun, AgentRunStatus
from apps.api.app.models.file_change import (
    FileChange,
    FileChangeOperation,
)
from apps.api.app.models.pull_request import (
    ApprovalStatus,
    PullRequest,
)
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
from apps.api.app.models.task_step import (
    AgentType,
    TaskStep,
    TaskStepStatus,
)
from apps.api.app.models.test_run import (
    TestRun as TestRunModel,
)
from apps.api.app.models.test_run import (
    TestRunStatus as TestRunStatusModel,
)
from ingestion.change_context.models import RepositoryChangeContext


class FakeTaskPersistence:
    def __init__(
        self,
        task: Task,
        repository: Repository,
    ) -> None:
        self.task = task
        self.repository = repository
        self.statuses: list[TaskStatus] = []

    async def get_task(self, task_id: UUID) -> Task | None:
        if task_id != self.task.id:
            return None
        return self.task

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
    ) -> Task | None:
        if task_id != self.task.id:
            return None

        self.task.status = status
        self.statuses.append(status)
        return self.task

    async def get_repository(
        self,
        repository_id: UUID,
    ) -> Repository | None:
        if repository_id != self.repository.id:
            return None
        return self.repository


class FakePlanningContextBuilder:
    def __init__(self, context: PlanningContext) -> None:
        self.context = context

    async def build(
        self,
        repository_id: UUID,
        task_description: str,
        repository_path: Path,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
    ) -> PlanningContext:
        return self.context


class FakePlanner:
    def __init__(self, plan: ImplementationPlan) -> None:
        self.plan_result = plan

    async def generate_plan(
        self,
        context: PlanningContext,
        *,
        max_tokens: int = 4096,
    ) -> ImplementationPlan:
        return self.plan_result


class FakeImplementationContextBuilder:
    def __init__(self, context: ImplementationContext) -> None:
        self.context = context

    def build(
        self,
        *,
        repository_id: UUID,
        repository_path: Path,
        task_description: str,
        change_context: RepositoryChangeContext,
        plan: ImplementationPlan,
    ) -> ImplementationContext:
        return self.context


class FakeImplementer:
    def __init__(
        self,
        implementation: ImplementationResult,
    ) -> None:
        self.implementation = implementation

    async def implement(
        self,
        context: ImplementationContext,
        plan: ImplementationPlan,
        *,
        max_tokens: int = 8192,
    ) -> ImplementationResult:
        return self.implementation


class FakeExecution:
    def __init__(
        self,
        result: ExecutionResult,
    ) -> None:
        self.result = result
        self.calls = 0

    def execute(
        self,
        workspace_path: Path,
        implementation: ImplementationResult,
    ) -> ExecutionResult:
        self.calls += 1
        return self.result


class FakeDebugger:
    async def debug(
        self,
        workspace_path: Path,
        context: ImplementationContext,
    ) -> NoReturn:
        raise AssertionError(
            "Debugger should not run for a passing execution."
        )


class FakeReviewer:
    async def review(
        self,
        *,
        context: ImplementationContext,
        implementation: ImplementationResult,
    ) -> ReviewResult:
        return ReviewResult(
            decision=ReviewDecision.APPROVE,
            summary="Review completed.",
            findings=(),
        )


class FakeWorkspace:
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self.created = 0
        self.removed: list[Path] = []

    def create_from_repository(
        self,
        repository_path: Path,
        *,
        branch_name: str | None = None,
    ) -> Path:
        self.created += 1
        return self.workspace_path

    def info(
        self,
        workspace_path: Path,
    ) -> WorkspaceInfo:
        return cast(
            WorkspaceInfo,
            SimpleNamespace(
                path=workspace_path,
                branch_name="repopilot/integration",
                commit_sha="integration-sha",
                is_clean=True,
            ),
        )

    def remove(self, workspace_path: Path) -> None:
        self.removed.append(workspace_path)


class FakeRepositorySource:
    def __init__(self, repository_path: Path) -> None:
        self.repository_path = repository_path

    async def prepare(
        self,
        repository: Repository,
    ) -> Path:
        return self.repository_path


class FakePullRequest:
    def __init__(self) -> None:
        self.pull_request_id = uuid4()
        self.calls = 0

    async def create_pull_request_from_implementation(
        self,
        *,
        repository: Repository,
        task: Task,
        implementation: ImplementationResult,
        branch_name: str,
        title: str,
        body: str,
    ) -> PullRequest:
        self.calls += 1
        return cast(
            PullRequest,
            SimpleNamespace(id=self.pull_request_id),
        )


class FakeApproval:
    async def get_status(
        self,
        request: ApprovalRequest,
    ) -> ApprovalResult:
        return ApprovalResult(
            pull_request_id=request.pull_request_id,
            status=ApprovalStatus.PENDING,
        )

    async def require_approval(
        self,
        pull_request_id: UUID,
    ) -> ApprovalResult:
        return ApprovalResult(
            pull_request_id=pull_request_id,
            status=ApprovalStatus.PENDING,
        )


class ApplyingFakeExecution:
    def __init__(
        self,
        result: ExecutionResult,
        source: Path,
        after_content: str,
    ) -> None:
        self.result = result
        self.source = source
        self.after_content = after_content
        self.calls = 0

    def execute(
        self,
        workspace_path: Path,
        implementation: ImplementationResult,
    ) -> ExecutionResult:
        self.calls += 1
        self.source.write_text(
            self.after_content,
            encoding="utf-8",
        )
        return self.result


def make_planning_context(
    repository_id: UUID,
) -> PlanningContext:
    change_context = RepositoryChangeContext(
        repository_id=repository_id,
        task_description="Fix authentication.",
        files=(),
        symbols=(),
        dependencies=(),
    )

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
        files_to_modify=(
            PlannedFile(
                file_path="auth.py",
                reason="Update authentication validation.",
            ),
        ),
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
                content=(
                    "def authenticate(token: str) -> bool:\n"
                    "    return token == 'valid'\n"
                ),
                reason="Implement authentication validation.",
            ),
        ),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_persists_coding_artifacts(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    repository = Repository(
        owner="integration",
        name=f"orchestrator-{uuid4().hex[:12]}",
        full_name=f"integration/orchestrator-{uuid4().hex[:12]}",
        github_repo_id=uuid4().int % 1_000_000_000,
        default_branch="main",
        description="Orchestrator artifact integration test",
        is_private=False,
        clone_url="https://github.com/integration/orchestrator-test.git",
    )
    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    task = Task(
        repository_id=repository.id,
        title="Fix authentication",
        description="Fix authentication.",
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    repository_path = tmp_path / "repository"
    repository_path.mkdir()

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    source = workspace_path / "auth.py"

    before_content = (
        "def authenticate(token: str) -> bool:\n"
        "    return False\n"
    )

    after_content = (
        "def authenticate(token: str) -> bool:\n"
        "    return token == 'valid'\n"
    )

    source.write_text(
        before_content,
        encoding="utf-8",
    )

    implementation = make_implementation()

    diff = (
        "--- a/auth.py\n"
        "+++ b/auth.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def authenticate(token: str) -> bool:\n"
        "-    return False\n"
        "+    return token == 'valid'\n"
    )

    application_result = ChangeApplicationResult(
        changes=(
            AppliedChange(
                file_path="auth.py",
                status=AppliedChangeStatus.APPLIED,
                operation=ChangeOperation.MODIFY.value,
                diff=diff,
            ),
        ),
        files_changed=1,
        dry_run=False,
    )

    test_result = TestResult(
        status=TestStatus.PASSED,
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="1 passed",
        stderr="",
        duration_seconds=0.05,
        test_count=1,
        failure_count=0,
    )

    execution_result = ExecutionResult(
        status=ExecutionStatus.PASSED,
        changes=application_result,
        tests=test_result,
    )

    artifacts = SqlAlchemyArtifactPersistence(
        session=db_session,
        model_provider="ollama",
        model_name="qwen2.5-coder:3b",
    )

    dependencies = OrchestrationDependencies(
        persistence=FakeTaskPersistence(task, repository),
        artifacts=artifacts,
        repository_source=FakeRepositorySource(repository_path),
        planning_context_builder=FakePlanningContextBuilder(
            make_planning_context(repository.id),
        ),
        planner=FakePlanner(make_plan()),
        implementation_context_builder=FakeImplementationContextBuilder(
            make_implementation_context(repository.id),
        ),
        implementer=FakeImplementer(implementation),
        workspace=FakeWorkspace(workspace_path),
        execution=ApplyingFakeExecution(
            execution_result,
            source,
            after_content,
        ),
        debugger=FakeDebugger(),
        reviewer=FakeReviewer(),
        approval=FakeApproval(),
        pull_request=FakePullRequest(),
    )

    service = OrchestrationService(dependencies)

    result = await service.run(task.id)

    assert result.status.value == "waiting_approval"

    task_steps = (
        await db_session.scalars(
            select(TaskStep).where(
                TaskStep.task_id == task.id,
            ),
        )
    ).all()

    assert len(task_steps) == 1

    coding_step = task_steps[0]

    assert coding_step.agent_type == AgentType.CODING
    assert coding_step.status == TaskStepStatus.COMPLETED
    assert coding_step.output_data is not None

    agent_runs = (
        await db_session.scalars(
            select(AgentRun).where(
                AgentRun.task_step_id == coding_step.id,
            ),
        )
    ).all()

    assert len(agent_runs) == 1

    coding_run = agent_runs[0]

    assert coding_run.agent_type == AgentType.CODING
    assert coding_run.status == AgentRunStatus.COMPLETED
    assert coding_run.model_provider == "ollama"
    assert coding_run.model_name == "qwen2.5-coder:3b"

    changes = (
        await db_session.scalars(
            select(FileChange).where(
                FileChange.agent_run_id == coding_run.id,
            ),
        )
    ).all()

    assert len(changes) == 1

    change = changes[0]

    assert change.file_path == "auth.py"
    assert change.operation == FileChangeOperation.MODIFIED
    assert change.before_content == before_content
    assert change.after_content == after_content
    assert change.before_hash is not None
    assert change.after_hash is not None
    assert change.before_hash != change.after_hash
    assert change.diff == diff
    assert change.line_additions == 1
    assert change.line_deletions == 1

    test_runs = (
        await db_session.scalars(
            select(TestRunModel).where(
                TestRunModel.agent_run_id == coding_run.id,
            ),
        )
    ).all()

    assert len(test_runs) == 1

    test_run = test_runs[0]

    assert test_run.status == TestRunStatusModel.PASSED
    assert test_run.command == "python -m pytest -q"
    assert test_run.exit_code == 0
    assert test_run.stdout == "1 passed"
    assert test_run.stderr == ""
    assert test_run.duration_ms == 50
    assert test_run.working_directory == str(workspace_path)

    assert task.status == TaskStatus.WAITING_APPROVAL
