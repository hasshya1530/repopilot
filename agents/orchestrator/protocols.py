from pathlib import Path
from typing import Protocol
from uuid import UUID

from agents.approval.models import ApprovalRequest, ApprovalResult
from agents.debugger.models import DebuggerResult
from agents.execution.models import ExecutionResult
from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult
from agents.planner.models import PlanningContext
from agents.planner.plan_models import ImplementationPlan
from agents.reviewer.models import ReviewResult
from agents.workspace.models import WorkspaceInfo
from apps.api.app.models.pull_request import PullRequest
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
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
