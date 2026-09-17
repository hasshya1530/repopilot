from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ArchitectureComponentType(StrEnum):
    """Supported repository architecture component types."""

    MODULE = "module"
    PACKAGE = "package"
    SERVICE = "service"
    UNKNOWN = "unknown"


class ArchitectureDependencyType(StrEnum):
    """Supported architecture dependency types."""

    IMPORTS = "imports"
    CALLS = "calls"


@dataclass(frozen=True, slots=True)
class ArchitectureComponent:
    """A logical component discovered in a repository."""

    name: str
    component_type: ArchitectureComponentType
    files: tuple[str, ...]
    symbols: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureDependency:
    """A dependency between two architecture components."""

    source: str
    target: str
    dependency_type: ArchitectureDependencyType


@dataclass(frozen=True, slots=True)
class ArchitectureReport:
    """Aggregated architectural representation of a repository."""

    repository_id: UUID
    components: tuple[ArchitectureComponent, ...]
    dependencies: tuple[ArchitectureDependency, ...]
    entry_points: tuple[str, ...]
