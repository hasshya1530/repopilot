from dataclasses import dataclass
from uuid import UUID

from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
)


@dataclass(frozen=True, slots=True)
class PlanningConstraint:
    """A constraint that the implementation plan must respect."""

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
