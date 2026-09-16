from pathlib import Path
from uuid import UUID, uuid4

import pytest

from ingestion.context.models import RepositoryContext, RepositoryContextItem
from ingestion.graph.extraction.service import (
    RepositoryRelationshipExtractionService,
)
from ingestion.graph.models import RepositorySymbol, SymbolRelation
from ingestion.graph.parsers.registry import RelationshipParserRegistry
from ingestion.graph.service import RepositoryGraphService


class FakeContextService:
    def __init__(self, context: RepositoryContext) -> None:
        self._context = context

    async def build_context(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> RepositoryContext:
        return self._context


@pytest.mark.asyncio
async def test_build_graph_resolves_repository_relationships(
    tmp_path: Path,
) -> None:
    repository_id = uuid4()

    auth_file = tmp_path / "auth.py"
    api_file = tmp_path / "api.py"

    auth_file.write_text(
        """class AuthService:
    def login(self):
        pass
"""
    )

    api_file.write_text(
        """from auth import AuthService

def handle():
    service = AuthService()
    service.login()
"""
    )

    context = RepositoryContext(
        repository_id=repository_id,
        query="authentication",
        items=(
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="auth.py",
                symbol_name="__module__",
                symbol_type="module",
                start_line=1,
                end_line=3,
                content=auth_file.read_text(),
                score=0.9,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="auth.py",
                symbol_name="AuthService",
                symbol_type="class",
                start_line=1,
                end_line=3,
                content=auth_file.read_text(),
                score=0.9,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="api.py",
                symbol_name="__module__",
                symbol_type="module",
                start_line=1,
                end_line=6,
                content=api_file.read_text(),
                score=0.8,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="api.py",
                symbol_name="handle",
                symbol_type="function",
                start_line=3,
                end_line=6,
                content="""def handle():
    service = AuthService()
    service.login()
""",
                score=0.8,
            ),
        ),
    )

    context_service = FakeContextService(context)

    extraction_service = RepositoryRelationshipExtractionService(
        RelationshipParserRegistry(),
    )

    graph_service = RepositoryGraphService(
        context_service,
        extraction_service,
    )

    graph = await graph_service.build_graph(
        repository_id=repository_id,
        query="authentication",
        repository_path=tmp_path,
    )

    assert len(graph.symbols) == 4

    relationships = {
        (
            edge.relation,
            graph_symbol_name(graph.symbols, edge.source),
            graph_symbol_name(graph.symbols, edge.target),
        )
        for edge in graph.edges
    }

    assert (
        SymbolRelation.IMPORTS,
        "__module__",
        "AuthService",
    ) in relationships


def graph_symbol_name(
    symbols: tuple[RepositorySymbol, ...],
    symbol_id: UUID,
) -> str:
    for symbol in symbols:
        if symbol.symbol_id == symbol_id:
            return symbol.name

    raise AssertionError(f"Unknown symbol ID: {symbol_id}")
