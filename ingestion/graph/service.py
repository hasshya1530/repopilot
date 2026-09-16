from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid5

from ingestion.context.models import RepositoryContext, RepositoryContextItem
from ingestion.graph.extraction.service import (
    RepositoryRelationshipExtractionService,
)
from ingestion.graph.models import (
    RepositoryGraph,
    RepositorySymbol,
    SymbolEdge,
    SymbolRelation,
    SymbolRelationship,
)
from ingestion.graph.resolver import SymbolResolver


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
    """Build a deterministic symbol and relationship graph."""

    def __init__(
        self,
        context_service: ContextServiceProtocol,
        relationship_extraction_service: (
            RepositoryRelationshipExtractionService | None
        ) = None,
    ) -> None:
        self._context_service = context_service
        self._relationship_extraction_service = relationship_extraction_service

    async def build_graph(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = 20,
        repository_path: Path | None = None,
    ) -> RepositoryGraph:
        """Build a graph from repository context and source relationships."""
        context = await self._context_service.build_context(
            repository_id=repository_id,
            query=query,
            limit=limit,
        )

        symbols, symbol_ids = self._build_symbols(
            repository_id,
            context.items,
        )

        edges = self._build_containment_edges(
            context.items,
            symbol_ids,
        )

        relationship_extraction_service = self._relationship_extraction_service

        if relationship_extraction_service is not None and repository_path is not None:
            relationships = relationship_extraction_service.extract_repository(
                repository_path
            )

            edges.extend(
                self._build_relationship_edges(
                    relationships,
                    symbols,
                )
            )

        return RepositoryGraph(
            repository_id=repository_id,
            symbols=tuple(symbols),
            edges=tuple(edges),
        )

    @staticmethod
    def _build_symbols(
        repository_id: UUID,
        items: tuple[RepositoryContextItem, ...],
    ) -> tuple[list[RepositorySymbol], dict[tuple[str, str, int, int], UUID]]:
        symbols: list[RepositorySymbol] = []
        symbol_ids: dict[tuple[str, str, int, int], UUID] = {}

        for item in items:
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

        return symbols, symbol_ids

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

    @staticmethod
    def _build_relationship_edges(
        relationships: list[SymbolRelationship],
        symbols: list[RepositorySymbol],
    ) -> list[SymbolEdge]:
        resolver = SymbolResolver(symbols)
        edges: list[SymbolEdge] = []

        for relationship in relationships:
            resolved = resolver.resolve(relationship)

            if resolved is None:
                continue

            source_id, target_id = resolved

            edges.append(
                SymbolEdge(
                    source=source_id,
                    target=target_id,
                    relation=relationship.relation,
                )
            )

        return edges
