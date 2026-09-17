from collections import defaultdict
from typing import Protocol
from uuid import UUID

from ingestion.architecture.errors import ArchitectureAggregationError
from ingestion.architecture.models import (
    ArchitectureComponent,
    ArchitectureComponentType,
    ArchitectureDependency,
    ArchitectureDependencyType,
    ArchitectureReport,
)
from ingestion.graph.models import (
    RepositoryGraph,
    RepositorySymbol,
    SymbolRelation,
)


class GraphServiceProtocol(Protocol):
    """Protocol for repository graph services."""

    async def build_graph(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> RepositoryGraph:
        ...


class RepositoryArchitectureService:
    """Aggregate a repository graph into an architectural report."""

    def __init__(
        self,
        graph_service: GraphServiceProtocol,
    ) -> None:
        self._graph_service = graph_service

    async def analyze(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = 50,
    ) -> ArchitectureReport:
        """Build an architectural report from the repository graph."""
        try:
            graph = await self._graph_service.build_graph(
                repository_id=repository_id,
                query=query,
                limit=limit,
            )

            components = self._build_components(graph.symbols)
            dependencies = self._build_dependencies(graph)
            entry_points = self._find_entry_points(graph)

            return ArchitectureReport(
                repository_id=repository_id,
                components=tuple(components),
                dependencies=tuple(dependencies),
                entry_points=tuple(entry_points),
            )
        except ArchitectureAggregationError:
            raise
        except Exception as exc:
            raise ArchitectureAggregationError(
                "Failed to aggregate repository architecture."
            ) from exc

    @staticmethod
    def _build_components(
        symbols: tuple[RepositorySymbol, ...],
    ) -> list[ArchitectureComponent]:
        files_to_symbols: dict[str, list[str]] = defaultdict(list)

        for symbol in symbols:
            if symbol.name == "__module__":
                continue

            files_to_symbols[symbol.file_path].append(symbol.name)

        components: list[ArchitectureComponent] = []

        for file_path in sorted(files_to_symbols):
            symbol_names = tuple(
                sorted(set(files_to_symbols[file_path]))
            )

            components.append(
                ArchitectureComponent(
                    name=file_path,
                    component_type=ArchitectureComponentType.MODULE,
                    files=(file_path,),
                    symbols=symbol_names,
                )
            )

        return components

    @staticmethod
    def _build_dependencies(
        graph: RepositoryGraph,
    ) -> list[ArchitectureDependency]:
        symbol_by_id = {
            symbol.symbol_id: symbol
            for symbol in graph.symbols
        }

        dependencies: set[
            tuple[str, str, ArchitectureDependencyType]
        ] = set()

        for edge in graph.edges:
            if edge.relation == SymbolRelation.IMPORTS:
                dependency_type = ArchitectureDependencyType.IMPORTS
            elif edge.relation == SymbolRelation.CALLS:
                dependency_type = ArchitectureDependencyType.CALLS
            else:
                continue

            source = symbol_by_id.get(edge.source)
            target = symbol_by_id.get(edge.target)

            if source is None or target is None:
                continue

            if source.file_path == target.file_path:
                continue

            dependencies.add(
                (
                    source.file_path,
                    target.file_path,
                    dependency_type,
                )
            )

        return [
            ArchitectureDependency(
                source=source,
                target=target,
                dependency_type=dependency_type,
            )
            for source, target, dependency_type in sorted(
                dependencies,
                key=lambda item: (
                    item[0],
                    item[1],
                    item[2].value,
                ),
            )
        ]

    @staticmethod
    def _find_entry_points(
        graph: RepositoryGraph,
    ) -> list[str]:
        entry_points: set[str] = set()

        for symbol in graph.symbols:
            if symbol.name in {
                "main",
                "__main__",
                "app",
                "application",
            }:
                entry_points.add(symbol.file_path)

        return sorted(entry_points)
