from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID

from agents.approval.models import ApprovalResult
from agents.debugger.models import DebuggerResult
from agents.execution.models import ExecutionResult
from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult
from agents.planner.models import PlanningContext
from agents.planner.plan_models import ImplementationPlan
from agents.reviewer.models import ReviewResult
from apps.api.app.models.pull_request import PullRequest


class OrchestrationStatus(StrEnum):
    PENDING = "pending"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    DEBUGGING = "debugging"
    REVIEWING = "reviewing"
    WAITING_APPROVAL = "waiting_approval"
    CREATING_PR = "creating_pr"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrchestrationStepType(StrEnum):
    UNDERSTAND = "understand"
    PLAN = "plan"
    IMPLEMENT = "implement"
    EXECUTE = "execute"
    DEBUG = "debug"
    REVIEW = "review"
    APPROVAL = "approval"
    CREATE_PR = "create_pr"


@dataclass(frozen=True, slots=True)
class OrchestrationState:
    task_id: UUID
    repository_id: UUID
    status: OrchestrationStatus
    current_step: OrchestrationStepType | None = None
    attempt: int = 0
    max_debug_attempts: int = 3
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationArtifacts:
    """Artifacts produced while executing an orchestration."""

    planning_context: PlanningContext | None = None
    plan: ImplementationPlan | None = None
    implementation_context: ImplementationContext | None = None
    implementation: ImplementationResult | None = None
    execution: ExecutionResult | None = None
    debugger: DebuggerResult | None = None
    review: ReviewResult | None = None
    pull_request: PullRequest | None = None
    approval: ApprovalResult | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    task_id: UUID
    status: OrchestrationStatus
    summary: str
    pull_request_id: UUID | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
