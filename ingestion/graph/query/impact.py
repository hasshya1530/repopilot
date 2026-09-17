from uuid import UUID

from ingestion.graph.models import RepositoryGraph
from ingestion.graph.query.models import (
    DependencyQuery,
    ImpactAnalysisResult,
)
from ingestion.graph.query.traversal import DependencyTraversalService


class ImpactAnalysisService:
    """Analyze the repository impact of changing a symbol."""

    def __init__(
        self,
        graph: RepositoryGraph,
        traversal_service: DependencyTraversalService,
    ) -> None:
        self._graph = graph
        self._traversal_service = traversal_service
        self._symbols_by_id = {symbol.symbol_id: symbol for symbol in graph.symbols}

    def analyze(
        self,
        query: DependencyQuery,
    ) -> ImpactAnalysisResult:
        """Return symbols and files affected by the starting symbol."""

        dependencies = self._traversal_service.traverse(
            DependencyQuery(
                symbol_id=query.symbol_id,
                relation=query.relation,
                direction="incoming",
                max_depth=query.max_depth,
            )
        )

        affected_symbols = tuple(dependency.target for dependency in dependencies)

        affected_files = self._resolve_files(affected_symbols)

        return ImpactAnalysisResult(
            symbol_id=query.symbol_id,
            affected_symbols=affected_symbols,
            affected_files=affected_files,
            dependencies=dependencies,
            max_depth=query.max_depth,
        )

    def _resolve_files(
        self,
        symbol_ids: tuple[UUID, ...],
    ) -> tuple[str, ...]:
        """Resolve affected symbols to unique repository files."""

        files: list[str] = []
        seen: set[str] = set()

        for symbol_id in symbol_ids:
            symbol = self._symbols_by_id.get(symbol_id)

            if symbol is None or symbol.file_path in seen:
                continue

            seen.add(symbol.file_path)
            files.append(symbol.file_path)

        return tuple(files)
