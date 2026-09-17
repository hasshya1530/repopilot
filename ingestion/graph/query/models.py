from dataclasses import dataclass
from uuid import UUID

from ingestion.graph.models import SymbolRelation


@dataclass(frozen=True, slots=True)
class SymbolQuery:
    """Describe a repository symbol lookup."""

    name: str
    file_path: str | None = None
    symbol_type: str | None = None


@dataclass(frozen=True, slots=True)
class SymbolQueryResult:
    """A symbol returned by a graph query."""

    symbol: UUID
    file_path: str
    name: str
    symbol_type: str
    start_line: int
    end_line: int
    parent: str | None


@dataclass(frozen=True, slots=True)
class DependencyQuery:
    """Describe a dependency traversal from a symbol."""

    symbol_id: UUID
    relation: SymbolRelation | None = None
    direction: str = "outgoing"
    max_depth: int = 1


@dataclass(frozen=True, slots=True)
class DependencyResult:
    """A dependency discovered during graph traversal."""

    source: UUID
    target: UUID
    relation: SymbolRelation
    depth: int


@dataclass(frozen=True, slots=True)
class ImpactAnalysisResult:
    """Repository impact information for a symbol."""

    symbol_id: UUID
    affected_symbols: tuple[UUID, ...]
    affected_files: tuple[str, ...]
    max_depth: int
