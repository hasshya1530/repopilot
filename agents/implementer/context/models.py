from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ImplementationContextFile:
    file_path: str
    content: str
    reason: str


@dataclass(frozen=True, slots=True)
class ImplementationContextSymbol:
    symbol_id: UUID
    file_path: str
    name: str
    symbol_type: str
    start_line: int
    end_line: int
    content: str
    reason: str


@dataclass(frozen=True, slots=True)
class ImplementationContextDependency:
    source_symbol_id: UUID
    target_symbol_id: UUID
    relation: str
    depth: int


@dataclass(frozen=True, slots=True)
class ImplementationContext:
    repository_id: UUID
    task_description: str
    files: tuple[ImplementationContextFile, ...]
    symbols: tuple[ImplementationContextSymbol, ...]
    dependencies: tuple[ImplementationContextDependency, ...]
