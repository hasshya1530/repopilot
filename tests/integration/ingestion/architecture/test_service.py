from pathlib import Path
from uuid import UUID, uuid4

import pytest

from ingestion.architecture.models import (
    ArchitectureComponentType,
    ArchitectureDependencyType,
)
from ingestion.architecture.service import RepositoryArchitectureService
from ingestion.context.models import RepositoryContext, RepositoryContextItem
from ingestion.graph.extraction.service import (
    RepositoryRelationshipExtractionService,
)
from ingestion.graph.models import RepositoryGraph
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
async def test_repository_architecture_analysis(
    tmp_path: Path,
) -> None:
    repository_id = uuid4()

    auth_file = tmp_path / "auth.py"
    api_file = tmp_path / "api.py"
    main_file = tmp_path / "main.py"

    auth_source = """class AuthService:
    def login(self):
        pass
"""

    api_source = """from auth import AuthService

def handle():
    service = AuthService()
    service.login()
"""

    main_source = """from api import handle

def main():
    handle()
"""

    auth_file.write_text(auth_source)
    api_file.write_text(api_source)
    main_file.write_text(main_source)

    context = RepositoryContext(
        repository_id=repository_id,
        query="application architecture",
        items=(
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="auth.py",
                symbol_name="__module__",
                symbol_type="module",
                start_line=1,
                end_line=3,
                content=auth_source,
                score=0.9,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="auth.py",
                symbol_name="AuthService",
                symbol_type="class",
                start_line=1,
                end_line=3,
                content=auth_source,
                score=0.9,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="api.py",
                symbol_name="__module__",
                symbol_type="module",
                start_line=1,
                end_line=6,
                content=api_source,
                score=0.8,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="api.py",
                symbol_name="handle",
                symbol_type="function",
                start_line=3,
                end_line=6,
                content=api_source,
                score=0.8,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="main.py",
                symbol_name="__module__",
                symbol_type="module",
                start_line=1,
                end_line=4,
                content=main_source,
                score=0.7,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="main.py",
                symbol_name="main",
                symbol_type="function",
                start_line=3,
                end_line=4,
                content=main_source,
                score=0.7,
            ),
        ),
    )

    graph_service = RepositoryGraphService(
        FakeContextService(context),
        RepositoryRelationshipExtractionService(
            RelationshipParserRegistry(),
        ),
    )

    graph = await graph_service.build_graph(
        repository_id=repository_id,
        query="application architecture",
        repository_path=tmp_path,
    )

    architecture_service = RepositoryArchitectureService(
        FakeGraphService(graph),
    )

    report = await architecture_service.analyze(
        repository_id=repository_id,
        query="application architecture",
    )

    assert report.repository_id == repository_id

    assert {
        component.name
        for component in report.components
    } == {
        "auth.py",
        "api.py",
        "main.py",
    }

    auth_component = next(
        component
        for component in report.components
        if component.name == "auth.py"
    )

    assert auth_component.component_type == ArchitectureComponentType.MODULE
    assert auth_component.files == ("auth.py",)
    assert auth_component.symbols == ("AuthService",)

    api_component = next(
        component
        for component in report.components
        if component.name == "api.py"
    )

    assert api_component.symbols == ("handle",)

    main_component = next(
        component
        for component in report.components
        if component.name == "main.py"
    )

    assert main_component.symbols == ("main",)

    dependencies = {
        (
            dependency.source,
            dependency.target,
            dependency.dependency_type,
        )
        for dependency in report.dependencies
    }

    assert (
        "api.py",
        "auth.py",
        ArchitectureDependencyType.IMPORTS,
    ) in dependencies

    assert (
        "main.py",
        "api.py",
        ArchitectureDependencyType.IMPORTS,
    ) in dependencies

    assert report.entry_points == ("main.py",)
