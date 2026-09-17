"""Repository architecture analysis."""

from ingestion.architecture.errors import (
    ArchitectureAggregationError,
    ArchitectureConfigurationError,
    ArchitectureError,
)
from ingestion.architecture.models import (
    ArchitectureComponent,
    ArchitectureComponentType,
    ArchitectureDependency,
    ArchitectureDependencyType,
    ArchitectureReport,
)
from ingestion.architecture.service import RepositoryArchitectureService

__all__ = [
    "ArchitectureAggregationError",
    "ArchitectureConfigurationError",
    "ArchitectureComponent",
    "ArchitectureComponentType",
    "ArchitectureDependency",
    "ArchitectureDependencyType",
    "ArchitectureError",
    "ArchitectureReport",
    "RepositoryArchitectureService",
]
