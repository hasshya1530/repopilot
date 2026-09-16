from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class SymbolRelation(StrEnum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    CALLS = "calls"


@dataclass(frozen=True, slots=True)
class RepositorySymbol:
    symbol_id: UUID
    file_path: str
    name: str
    symbol_type: str
    start_line: int
    end_line: int
    parent: str | None = None


@dataclass(frozen=True, slots=True)
class SymbolEdge:
    source: UUID
    target: UUID
    relation: SymbolRelation


@dataclass(frozen=True, slots=True)
class RepositoryGraph:
    repository_id: UUID
    symbols: tuple[RepositorySymbol, ...]
    edges: tuple[SymbolEdge, ...]


@dataclass(frozen=True, slots=True)
class SymbolRelationship:
    """A source-level relationship before symbol resolution."""

    source_name: str
    target_name: str
    relation: SymbolRelation
    source_file: str
    target_file: str | None = None
