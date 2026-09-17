from ingestion.graph.models import RepositoryGraph, RepositorySymbol
from ingestion.graph.query.models import SymbolQuery, SymbolQueryResult


class SymbolQueryService:
    """Query repository symbols from a repository graph."""

    def __init__(self, graph: RepositoryGraph) -> None:
        self._graph = graph

    def find_symbols(self, query: SymbolQuery) -> tuple[SymbolQueryResult, ...]:
        """Find symbols matching the supplied query."""

        if not query.name.strip():
            return ()

        matches = [symbol for symbol in self._graph.symbols if self._matches(symbol, query)]

        return tuple(self._to_result(symbol) for symbol in matches)

    @staticmethod
    def _matches(
        symbol: RepositorySymbol,
        query: SymbolQuery,
    ) -> bool:
        if symbol.name != query.name:
            return False

        if query.file_path is not None and symbol.file_path != query.file_path:
            return False

        if query.symbol_type is not None and symbol.symbol_type != query.symbol_type:
            return False

        return True

    @staticmethod
    def _to_result(symbol: RepositorySymbol) -> SymbolQueryResult:
        return SymbolQueryResult(
            symbol=symbol.symbol_id,
            file_path=symbol.file_path,
            name=symbol.name,
            symbol_type=symbol.symbol_type,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
            parent=symbol.parent,
        )
