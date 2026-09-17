from typing import Any
from uuid import UUID, uuid4

import pytest

from ingestion.change_context.errors import (
    ChangeContextAnalysisError,
    ChangeContextConfigurationError,
    ChangeContextRetrievalError,
)
from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
    RepositoryChangeContext,
)
from ingestion.change_context.service import ChangeContextService
from ingestion.context.models import RepositoryContext, RepositoryContextItem
from ingestion.graph.models import SymbolRelation
from ingestion.graph.query.models import DependencyResult, ImpactAnalysisResult


class FakeContextService:
    def __init__(self, context: RepositoryContext) -> None:
        self.context = context

    async def build_context(
        self,
        repository_id: UUID,
        query: str,
        limit: int = 20,
    ) -> RepositoryContext:
        return self.context


class FailingContextService:
    async def build_context(
        self,
        repository_id: UUID,
        query: str,
        limit: int = 20,
    ) -> RepositoryContext:
        raise RuntimeError("retrieval failed")


class FakeImpactService:
    def __init__(self, result: ImpactAnalysisResult) -> None:
        self.result = result

    def analyze(self, query: Any) -> ImpactAnalysisResult:
        return self.result


class FailingImpactService:
    def analyze(self, query: Any) -> ImpactAnalysisResult:
        raise RuntimeError("analysis failed")


def build_context(repository_id: UUID) -> RepositoryContext:
    return RepositoryContext(
        repository_id=repository_id,
        query="authentication",
        items=(
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="auth.py",
                symbol_name="validate_token",
                symbol_type="function",
                start_line=10,
                end_line=20,
                content="def validate_token(): ...",
                score=0.95,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="service.py",
                symbol_name="get_user",
                symbol_type="function",
                start_line=5,
                end_line=12,
                content="def get_user(): ...",
                score=0.80,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="auth.py",
                symbol_name="refresh_token",
                symbol_type="function",
                start_line=25,
                end_line=30,
                content="def refresh_token(): ...",
                score=0.70,
            ),
        ),
    )


def build_impact() -> ImpactAnalysisResult:
    source = uuid4()
    target = uuid4()

    dependency = DependencyResult(
        source=source,
        target=target,
        relation=SymbolRelation.CALLS,
        depth=1,
    )

    return ImpactAnalysisResult(
        symbol_id=target,
        affected_symbols=(source,),
        affected_files=("auth.py",),
        dependencies=(dependency,),
        max_depth=2,
    )


@pytest.mark.asyncio
async def test_builds_change_context_from_repository_context() -> None:
    repository_id = uuid4()
    context = build_context(repository_id)

    service = ChangeContextService(
        context_service=FakeContextService(context),
        impact_service=FakeImpactService(build_impact()),
    )

    result = await service.build(
        repository_id=repository_id,
        task_description="Improve authentication",
    )

    assert isinstance(result, RepositoryChangeContext)
    assert result.repository_id == repository_id
    assert result.task_description == "Improve authentication"

    assert len(result.files) == 2
    assert result.files[0].file_path == "auth.py"
    assert result.files[1].file_path == "service.py"

    assert len(result.symbols) == 3
    assert result.symbols[0].name == "validate_token"

    assert result.dependencies == ()


@pytest.mark.asyncio
async def test_build_includes_impact_dependencies() -> None:
    repository_id = uuid4()
    impact = build_impact()

    service = ChangeContextService(
        context_service=FakeContextService(build_context(repository_id)),
        impact_service=FakeImpactService(impact),
    )

    result = await service.build(
        repository_id=repository_id,
        task_description="Change token validation",
        symbol_id=impact.symbol_id,
        max_depth=2,
    )

    assert len(result.dependencies) == 1

    dependency = result.dependencies[0]

    assert isinstance(dependency, ChangeContextDependency)
    assert dependency.source_symbol_id == impact.dependencies[0].source
    assert dependency.target_symbol_id == impact.dependencies[0].target
    assert dependency.relation == "calls"
    assert dependency.depth == 1


@pytest.mark.asyncio
async def test_rejects_empty_task_description() -> None:
    repository_id = uuid4()

    service = ChangeContextService(
        context_service=FakeContextService(build_context(repository_id)),
        impact_service=FakeImpactService(build_impact()),
    )

    with pytest.raises(ChangeContextConfigurationError):
        await service.build(
            repository_id=repository_id,
            task_description="   ",
        )


@pytest.mark.asyncio
async def test_rejects_invalid_context_limit() -> None:
    repository_id = uuid4()

    service = ChangeContextService(
        context_service=FakeContextService(build_context(repository_id)),
        impact_service=FakeImpactService(build_impact()),
    )

    with pytest.raises(ChangeContextConfigurationError):
        await service.build(
            repository_id=repository_id,
            task_description="authentication",
            context_limit=0,
        )


@pytest.mark.asyncio
async def test_rejects_invalid_max_depth() -> None:
    repository_id = uuid4()

    service = ChangeContextService(
        context_service=FakeContextService(build_context(repository_id)),
        impact_service=FakeImpactService(build_impact()),
    )

    with pytest.raises(ChangeContextConfigurationError):
        await service.build(
            repository_id=repository_id,
            task_description="authentication",
            max_depth=0,
        )


@pytest.mark.asyncio
async def test_wraps_context_retrieval_errors() -> None:
    repository_id = uuid4()

    service = ChangeContextService(
        context_service=FailingContextService(),
        impact_service=FakeImpactService(build_impact()),
    )

    with pytest.raises(ChangeContextRetrievalError):
        await service.build(
            repository_id=repository_id,
            task_description="authentication",
        )


@pytest.mark.asyncio
async def test_wraps_impact_analysis_errors() -> None:
    repository_id = uuid4()

    service = ChangeContextService(
        context_service=FakeContextService(build_context(repository_id)),
        impact_service=FailingImpactService(),
    )

    with pytest.raises(ChangeContextAnalysisError):
        await service.build(
            repository_id=repository_id,
            task_description="authentication",
            symbol_id=uuid4(),
        )


def test_build_files_deduplicates_file_paths() -> None:
    repository_id = uuid4()
    context = build_context(repository_id)

    files = ChangeContextService._build_files(context)

    assert len(files) == 2
    assert [item.file_path for item in files] == [
        "auth.py",
        "service.py",
    ]
    assert all(isinstance(item, ChangeContextFile) for item in files)


def test_build_symbols_preserves_retrieval_order() -> None:
    repository_id = uuid4()
    context = build_context(repository_id)

    symbols = ChangeContextService._build_symbols(context)

    assert [symbol.name for symbol in symbols] == [
        "validate_token",
        "get_user",
        "refresh_token",
    ]
    assert all(isinstance(item, ChangeContextSymbol) for item in symbols)


def test_build_dependencies_maps_graph_relationships() -> None:
    impact = build_impact()

    dependencies = ChangeContextService._build_dependencies(impact)

    assert len(dependencies) == 1
    assert dependencies[0].relation == "calls"
    assert dependencies[0].depth == 1
    assert isinstance(dependencies[0], ChangeContextDependency)
