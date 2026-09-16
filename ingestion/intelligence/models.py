from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RepositoryFileSummary:
    """Aggregated intelligence about a repository file."""

    file_path: str
    chunk_count: int
    best_score: float
    symbols: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RepositoryIntelligence:
    """Structured repository intelligence assembled from retrieved code."""

    repository_id: UUID
    query: str
    files: tuple[RepositoryFileSummary, ...]
