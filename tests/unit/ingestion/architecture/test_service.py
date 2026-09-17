from uuid import UUID, uuid4

import pytest

from ingestion.architecture.models import (
    ArchitectureComponentType,
    ArchitectureDependencyType,
)
from ingestion.architecture.service import RepositoryArchitectureService
from ingestion.graph.models import (
    RepositoryGraph,
    RepositorySymbol,
    SymbolEdge,
    SymbolRelation,
)


class FakeGraphService:
    def __init__(self, graph: RepositoryGraph) -> None:
        self._graph = graph

    async def build_graph(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> RepositoryGraph:
        return self._graph


@pytest.mark.asyncio
async def test_analyze_builds_components_and_dependencies() -> None:
    repository_id = uuid4()

    auth = RepositorySymbol(
        symbol_id=uuid4(),
        file_path="auth.py",
        name="AuthService",
        symbol_type="class",
        start_line=1,
        end_line=5,
    )

    login = RepositorySymbol(
        symbol_id=uuid4(),
        file_path="auth.py",
        name="login",
        symbol_type="function",
        start_line=2,
        end_line=5,
    )

    api = RepositorySymbol(
        symbol_id=uuid4(),
        file_path="api.py",
        name="handle",
        symbol_type="function",
        start_line=1,
        end_line=5,
    )

    graph = RepositoryGraph(
        repository_id=repository_id,
        symbols=(auth, login, api),
        edges=(
            SymbolEdge(
                source=api.symbol_id,
                target=auth.symbol_id,
                relation=SymbolRelation.IMPORTS,
            ),
        ),
    )

    service = RepositoryArchitectureService(
        FakeGraphService(graph),
    )

    report = await service.analyze(
        repository_id=repository_id,
        query="authentication",
    )

    assert report.repository_id == repository_id

    assert report.components == (
        report.components[0],
        report.components[1],
    )

    assert {
        component.name
        for component in report.components
    } == {
        "api.py",
        "auth.py",
    }

    auth_component = next(
        component
        for component in report.components
        if component.name == "auth.py"
    )

    assert auth_component.component_type == ArchitectureComponentType.MODULE
    assert auth_component.symbols == (
        "AuthService",
        "login",
    )

    assert report.dependencies == (
        report.dependencies[0],
    )

    dependency = report.dependencies[0]

    assert dependency.source == "api.py"
    assert dependency.target == "auth.py"
    assert dependency.dependency_type == ArchitectureDependencyType.IMPORTS


@pytest.mark.asyncio
async def test_analyze_detects_main_entry_point() -> None:
    repository_id = uuid4()

    main = RepositorySymbol(
        symbol_id=uuid4(),
        file_path="main.py",
        name="main",
        symbol_type="function",
        start_line=1,
        end_line=5,
    )

    graph = RepositoryGraph(
        repository_id=repository_id,
        symbols=(main,),
        edges=(),
    )

    service = RepositoryArchitectureService(
        FakeGraphService(graph),
    )

    report = await service.analyze(
        repository_id=repository_id,
        query="application",
    )

    assert report.entry_points == ("main.py",)


@pytest.mark.asyncio
async def test_analyze_ignores_containment_edges_as_dependencies() -> None:
    repository_id = uuid4()

    parent = RepositorySymbol(
        symbol_id=uuid4(),
        file_path="auth.py",
        name="AuthService",
        symbol_type="class",
        start_line=1,
        end_line=5,
    )

    child = RepositorySymbol(
        symbol_id=uuid4(),
        file_path="auth.py",
        name="login",
        symbol_type="method",
        start_line=2,
        end_line=5,
        parent="AuthService",
    )

    graph = RepositoryGraph(
        repository_id=repository_id,
        symbols=(parent, child),
        edges=(
            SymbolEdge(
                source=parent.symbol_id,
                target=child.symbol_id,
                relation=SymbolRelation.CONTAINS,
            ),
        ),
    )

    service = RepositoryArchitectureService(
        FakeGraphService(graph),
    )

    report = await service.analyze(
        repository_id=repository_id,
        query="authentication",
    )

    assert report.dependencies == ()
