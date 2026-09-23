from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class PlanStepType(StrEnum):
    """Types of actions represented by an implementation step."""

    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"
    TEST = "test"
    VALIDATE = "validate"


@dataclass(frozen=True, slots=True)
class ImplementationStep:
    """A single ordered implementation action."""

    order: int
    description: str
    step_type: PlanStepType
    file_path: str | None = None
    symbol_name: str | None = None


@dataclass(frozen=True, slots=True)
class PlannedFile:
    """A file involved in the implementation plan."""

    file_path: str
    reason: str


@dataclass(frozen=True, slots=True)
class PlannedSymbol:
    """A repository symbol targeted by the implementation."""

    symbol_id: UUID
    file_path: str
    name: str
    reason: str


@dataclass(frozen=True, slots=True)
class ImplementationPlan:
    """A structured implementation plan produced by the planner."""

    summary: str
    assumptions: tuple[str, ...]
    files_to_modify: tuple[PlannedFile, ...]
    files_to_create: tuple[PlannedFile, ...]
    test_files: tuple[PlannedFile, ...] = ()
    symbols_to_modify: tuple[PlannedSymbol, ...] = ()
    implementation_steps: tuple[ImplementationStep, ...] = ()
    dependencies: tuple[str, ...] = ()
    tests_to_add: tuple[str, ...] = ()
    validation_commands: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
