from pathlib import Path
from typing import Protocol
from uuid import UUID

from agents.approval.models import ApprovalRequest, ApprovalResult
from agents.debugger.models import DebuggerResult
from agents.execution.models import ExecutionResult
from agents.implementer.applier.models import ChangeApplicationResult
from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult
from agents.planner.models import PlanningContext
from agents.planner.plan_models import ImplementationPlan
from agents.reviewer.models import ReviewResult
from agents.workspace.models import WorkspaceInfo
from apps.api.app.models.agent_run import AgentRun
from apps.api.app.models.file_change import FileChange
from apps.api.app.models.pull_request import PullRequest
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
from apps.api.app.models.task_step import AgentType, TaskStep
from apps.api.app.models.test_run import TestRun
from apps.api.app.services.implementation_artifacts import FileSnapshot
from ingestion.change_context.models import RepositoryChangeContext


class PlannerProtocol(Protocol):
    async def generate_plan(
        self,
        context: PlanningContext,
        *,
        max_tokens: int = 4096,
    ) -> ImplementationPlan:
        ...


class ImplementerProtocol(Protocol):
    async def implement(
        self,
        context: ImplementationContext,
        plan: ImplementationPlan,
        *,
        max_tokens: int = 8192,
    ) -> ImplementationResult:
        ...


class ExecutionProtocol(Protocol):
    def execute(
        self,
        workspace_path: Path,
        implementation: ImplementationResult,
    ) -> ExecutionResult:
        ...


class DebuggerProtocol(Protocol):
    async def debug(
        self,
        workspace_path: Path,
        context: ImplementationContext,
        *,
        task_id: UUID | None = None,
    ) -> DebuggerResult:
        ...


class ReviewerProtocol(Protocol):
    async def review(
        self,
        *,
        context: ImplementationContext,
        implementation: ImplementationResult,
    ) -> ReviewResult:
        ...


class ApprovalProtocol(Protocol):
    async def get_status(
        self,
        request: ApprovalRequest,
    ) -> ApprovalResult:
        ...

    async def require_approval(
        self,
        pull_request_id: UUID,
    ) -> ApprovalResult:
        ...


class PullRequestProtocol(Protocol):
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
        ...


class PlanningContextBuilderProtocol(Protocol):
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
        ...


class ImplementationContextBuilderProtocol(Protocol):
    def build(
        self,
        *,
        repository_id: UUID,
        repository_path: Path,
        task_description: str,
        change_context: RepositoryChangeContext,
        plan: ImplementationPlan,
    ) -> ImplementationContext:
        ...


class WorkspaceProtocol(Protocol):
    def create_from_repository(
        self,
        repository_path: Path,
        *,
        branch_name: str | None = None,
    ) -> Path:
        ...

    def info(
        self,
        workspace_path: Path,
    ) -> WorkspaceInfo:
        ...

    def remove(
        self,
        workspace_path: Path,
    ) -> None:
        ...


class RepositorySourceProtocol(Protocol):
    async def prepare(
        self,
        repository: Repository,
    ) -> Path:
        ...


class TaskPersistenceProtocol(Protocol):
    async def get_task(
        self,
        task_id: UUID,
    ) -> Task | None:
        ...

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
    ) -> Task | None:
        ...

    async def get_repository(
        self,
        repository_id: UUID,
    ) -> Repository | None:
        ...


class ArtifactPersistenceProtocol(Protocol):
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
        ...

    async def complete_agent(
        self,
        *,
        task_step_id: UUID,
        agent_run_id: UUID,
        output_data: str | None = None,
    ) -> tuple[TaskStep | None, AgentRun | None]:
        ...

    async def fail_agent(
        self,
        *,
        task_step_id: UUID,
        agent_run_id: UUID,
        error_message: str,
    ) -> tuple[TaskStep | None, AgentRun | None]:
        ...

    def capture_snapshots(
        self,
        *,
        workspace_path: Path,
        implementation: ImplementationResult,
    ) -> dict[str, FileSnapshot]:
        ...

    async def persist_implementation(
        self,
        *,
        agent_run_id: UUID,
        workspace_path: Path,
        implementation: ImplementationResult,
        application_result: ChangeApplicationResult,
        snapshots: dict[str, FileSnapshot],
    ) -> list[FileChange]:
        ...

    async def persist_test_result(
        self,
        *,
        agent_run_id: UUID,
        workspace_path: Path,
        execution: ExecutionResult,
    ) -> TestRun:
        ...


class OrchestrationDependencies:
    def __init__(
        self,
        *,
        planner: PlannerProtocol,
        implementer: ImplementerProtocol,
        execution: ExecutionProtocol,
        debugger: DebuggerProtocol,
        reviewer: ReviewerProtocol,
        approval: ApprovalProtocol,
        pull_request: PullRequestProtocol,
        planning_context_builder: PlanningContextBuilderProtocol,
        implementation_context_builder: ImplementationContextBuilderProtocol,
        workspace: WorkspaceProtocol,
        repository_source: RepositorySourceProtocol,
        persistence: TaskPersistenceProtocol,
        artifacts: ArtifactPersistenceProtocol | None = None,
    ) -> None:
        self.planner = planner
        self.implementer = implementer
        self.execution = execution
        self.debugger = debugger
        self.reviewer = reviewer
        self.approval = approval
        self.pull_request = pull_request
        self.planning_context_builder = planning_context_builder
        self.implementation_context_builder = implementation_context_builder
        self.workspace = workspace
        self.repository_source = repository_source
        self.persistence = persistence
        self.artifacts = artifacts
