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
class RepositoryContext:
    """Structured repository context assembled from code retrieval."""

    repository_id: UUID
    query: str
    items: tuple[RepositoryContextItem, ...]
