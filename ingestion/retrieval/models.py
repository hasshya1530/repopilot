from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """A code chunk returned by semantic retrieval."""

    chunk_id: UUID
    repository_id: UUID
    file_path: str
    content: str
    symbol_name: str
    symbol_type: str
    start_line: int
    end_line: int
    parent: str | None
    score: float
