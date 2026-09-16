from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from ingestion.graph.models import RepositorySymbol, SymbolRelationship


class SymbolResolver:
    """Resolve source-level relationships to repository symbol IDs."""

    def __init__(self, symbols: Iterable[RepositorySymbol]) -> None:
        self._symbols = tuple(symbols)

        self._by_file_and_name: dict[tuple[str, str], list[RepositorySymbol]] = defaultdict(list)
        self._by_name: dict[str, list[RepositorySymbol]] = defaultdict(list)

        for symbol in self._symbols:
            self._by_file_and_name[(symbol.file_path, symbol.name)].append(symbol)
            self._by_name[symbol.name].append(symbol)

    def resolve(
        self,
        relationship: SymbolRelationship,
    ) -> tuple[UUID, UUID] | None:
        """Resolve a relationship to source and target symbol IDs."""

        source = self._resolve_source(relationship)
        if source is None:
            return None

        target = self._resolve_target(relationship)
        if target is None:
            return None

        return source.symbol_id, target.symbol_id

    def _resolve_source(
        self,
        relationship: SymbolRelationship,
    ) -> RepositorySymbol | None:
        candidates = self._by_file_and_name.get(
            (relationship.source_file, relationship.source_name),
            [],
        )

        if candidates:
            return self._select_candidate(candidates)

        return None

    def _resolve_target(
        self,
        relationship: SymbolRelationship,
    ) -> RepositorySymbol | None:
        if relationship.target_file is not None:
            candidates = self._by_file_and_name.get(
                (relationship.target_file, relationship.target_name),
                [],
            )

            if candidates:
                return self._select_candidate(candidates)

        candidates = self._by_name.get(relationship.target_name, [])

        if candidates:
            return self._select_candidate(candidates)

        return None

    @staticmethod
    def _select_candidate(
        candidates: list[RepositorySymbol],
    ) -> RepositorySymbol:
        return min(
            candidates,
            key=lambda symbol: (
                symbol.start_line,
                symbol.end_line,
                str(symbol.symbol_id),
            ),
        )
