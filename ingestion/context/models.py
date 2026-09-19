from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RepositoryContextItem:
    """A retrieved code chunk included in repository context."""

    chunk_id: UUID
    file_path: str
    symbol_name: str
    symbol_type: str
    start_line: int
    end_line: int
    content: str
    score: float
    parent: str | None = None


@dataclass(frozen=True, slots=True)
class RepositoryContextFile:
    """Code chunks grouped under one repository file."""

    file_path: str
    items: tuple[RepositoryContextItem, ...]
    score: float


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    """Structured, bounded repository context assembled from code retrieval."""

    repository_id: UUID
    query: str
    items: tuple[RepositoryContextItem, ...]
    files: tuple[RepositoryContextFile, ...] = ()
    total_candidates: int = 0
    truncated: bool = False
    character_count: int = 0
