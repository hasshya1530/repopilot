from uuid import UUID, uuid4

import pytest

from ingestion.context.models import RepositoryContext, RepositoryContextItem
from ingestion.graph.models import SymbolRelation
from ingestion.graph.service import RepositoryGraphService


class FakeContextService:
    def __init__(self, context: RepositoryContext) -> None:
        self.context = context

    async def build_context(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> RepositoryContext:
        return self.context


@pytest.mark.asyncio
async def test_build_graph_creates_unique_symbols() -> None:
    repository_id = uuid4()

    context = RepositoryContext(
        repository_id=repository_id,
        query="authentication",
        items=(
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/auth.py",
                symbol_name="login",
                symbol_type="function",
                start_line=1,
                end_line=5,
                content="def login(): pass",
                score=0.9,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/auth.py",
                symbol_name="login",
                symbol_type="function",
                start_line=1,
                end_line=5,
                content="def login(): pass",
                score=0.8,
            ),
        ),
    )

    service = RepositoryGraphService(
        FakeContextService(context),
    )

    graph = await service.build_graph(
        repository_id=repository_id,
        query="authentication",
    )

    assert len(graph.symbols) == 1
    assert graph.symbols[0].name == "login"
    assert graph.edges == ()


@pytest.mark.asyncio
async def test_build_graph_creates_contains_relationship() -> None:
    repository_id = uuid4()

    context = RepositoryContext(
        repository_id=repository_id,
        query="authentication",
        items=(
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/auth.py",
                symbol_name="AuthService",
                symbol_type="class",
                start_line=1,
                end_line=10,
                content="class AuthService: pass",
                score=0.9,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/auth.py",
                symbol_name="login",
                symbol_type="method",
                start_line=3,
                end_line=6,
                content="def login(): pass",
                score=0.8,
                parent="AuthService",
            ),
        ),
    )

    service = RepositoryGraphService(
        FakeContextService(context),
    )

    graph = await service.build_graph(
        repository_id=repository_id,
        query="authentication",
    )

    assert len(graph.symbols) == 2
    assert len(graph.edges) == 1

    edge = graph.edges[0]

    assert edge.relation == SymbolRelation.CONTAINS
    assert edge.source != edge.target


@pytest.mark.asyncio
async def test_build_graph_returns_empty_graph_for_empty_context() -> None:
    repository_id = uuid4()

    context = RepositoryContext(
        repository_id=repository_id,
        query="authentication",
        items=(),
    )

    service = RepositoryGraphService(
        FakeContextService(context),
    )

    graph = await service.build_graph(
        repository_id=repository_id,
        query="authentication",
    )

    assert graph.symbols == ()
    assert graph.edges == ()
