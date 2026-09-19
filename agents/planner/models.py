from dataclasses import dataclass
from uuid import UUID

from agents.planner.plan_models import ImplementationPlan
from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
    RepositoryChangeContext,
)
from ingestion.context.models import RepositoryContext


@dataclass(frozen=True, slots=True)
class PlanningConstraint:
    """A deterministic constraint supplied to the planner."""

    name: str
    description: str


@dataclass(frozen=True, slots=True)
class PlanningContext:
    """Structured repository context consumed by the planner."""

    repository_id: UUID
    task_description: str
    files: tuple[ChangeContextFile, ...]
    symbols: tuple[ChangeContextSymbol, ...]
    dependencies: tuple[ChangeContextDependency, ...]
    constraints: tuple[PlanningConstraint, ...]
    change_context: RepositoryChangeContext | None = None
    repository_context: RepositoryContext | None = None


@dataclass(frozen=True, slots=True)
class PlanningResult:
    """Result of a planning operation."""

    context: PlanningContext
    plan: ImplementationPlan
