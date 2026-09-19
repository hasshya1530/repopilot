from dataclasses import dataclass
from uuid import UUID

from ingestion.context.models import RepositoryContext


@dataclass(frozen=True, slots=True)
class ChangeContextFile:
    """A repository file relevant to a proposed change."""

    file_path: str
    reason: str
    relevance_score: float


@dataclass(frozen=True, slots=True)
class ChangeContextSymbol:
    """A repository symbol relevant to a proposed change."""

    symbol_id: UUID
    file_path: str
    name: str
    symbol_type: str
    start_line: int
    end_line: int
    reason: str


@dataclass(frozen=True, slots=True)
class ChangeContextDependency:
    """A dependency between repository symbols."""

    source_symbol_id: UUID
    target_symbol_id: UUID
    relation: str
    depth: int


@dataclass(frozen=True, slots=True)
class RepositoryChangeContext:
    """Complete repository context for a proposed change."""

    repository_id: UUID
    task_description: str
    files: tuple[ChangeContextFile, ...]
    symbols: tuple[ChangeContextSymbol, ...]
    dependencies: tuple[ChangeContextDependency, ...]
    repository_context: RepositoryContext | None = None
