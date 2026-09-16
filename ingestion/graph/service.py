from typing import Protocol
from uuid import UUID, uuid5

from ingestion.context.models import RepositoryContext, RepositoryContextItem
from ingestion.graph.models import (
    RepositoryGraph,
    RepositorySymbol,
    SymbolEdge,
    SymbolRelation,
)


class ContextServiceProtocol(Protocol):
    """Protocol for repository context services."""

    async def build_context(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> RepositoryContext:
        ...


class RepositoryGraphService:
    """Build a deterministic symbol graph from repository context."""

    def __init__(
        self,
        context_service: ContextServiceProtocol,
    ) -> None:
        self._context_service = context_service

    async def build_graph(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = 20,
    ) -> RepositoryGraph:
        """Build a graph from the symbols present in repository context."""
        context = await self._context_service.build_context(
            repository_id=repository_id,
            query=query,
            limit=limit,
        )

        symbols: list[RepositorySymbol] = []
        symbol_ids: dict[tuple[str, str, int, int], UUID] = {}

        for item in context.items:
            key = (
                item.file_path,
                item.symbol_name,
                item.start_line,
                item.end_line,
            )

            if key in symbol_ids:
                continue

            symbol_id = uuid5(
                repository_id,
                ":".join(
                    [
                        item.file_path,
                        item.symbol_name,
                        str(item.start_line),
                        str(item.end_line),
                    ]
                ),
            )

            symbol_ids[key] = symbol_id

            symbols.append(
                RepositorySymbol(
                    symbol_id=symbol_id,
                    file_path=item.file_path,
                    name=item.symbol_name,
                    symbol_type=item.symbol_type,
                    start_line=item.start_line,
                    end_line=item.end_line,
                    parent=item.parent,
                )
            )

        edges = self._build_containment_edges(
            context.items,
            symbol_ids,
        )

        return RepositoryGraph(
            repository_id=repository_id,
            symbols=tuple(symbols),
            edges=tuple(edges),
        )

    @staticmethod
    def _build_containment_edges(
        items: tuple[RepositoryContextItem, ...],
        symbol_ids: dict[tuple[str, str, int, int], UUID],
    ) -> list[SymbolEdge]:
        edges: list[SymbolEdge] = []

        symbols_by_file: dict[str, list[RepositoryContextItem]] = {}

        for item in items:
            symbols_by_file.setdefault(item.file_path, []).append(item)

        for file_items in symbols_by_file.values():
            for item in file_items:
                if item.parent is None:
                    continue

                child_key = (
                    item.file_path,
                    item.symbol_name,
                    item.start_line,
                    item.end_line,
                )

                parent_candidates = [
                    candidate
                    for candidate in file_items
                    if candidate.symbol_name == item.parent
                ]

                if not parent_candidates:
                    continue

                parent = parent_candidates[0]

                parent_key = (
                    parent.file_path,
                    parent.symbol_name,
                    parent.start_line,
                    parent.end_line,
                )

                edges.append(
                    SymbolEdge(
                        source=symbol_ids[parent_key],
                        target=symbol_ids[child_key],
                        relation=SymbolRelation.CONTAINS,
                    )
                )

        return edges
