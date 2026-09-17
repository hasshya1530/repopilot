from uuid import UUID, uuid4

import pytest

from agents.planner.errors import PlanningContextError
from agents.planner.service import PlanningContextService
from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
    RepositoryChangeContext,
)


class FakeChangeContextService:
    def __init__(self, context: RepositoryChangeContext) -> None:
        self.context = context

    async def build(
        self,
        repository_id: UUID,
        task_description: str,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
    ) -> RepositoryChangeContext:
        return self.context


class FailingChangeContextService:
    async def build(
        self,
        repository_id: UUID,
        task_description: str,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
    ) -> RepositoryChangeContext:
        raise RuntimeError("change context failed")


def build_context(
    repository_id: UUID,
    *,
    include_dependencies: bool = True,
) -> RepositoryChangeContext:
    dependencies: tuple[ChangeContextDependency, ...] = ()

    if include_dependencies:
        dependencies = (
            ChangeContextDependency(
                source_symbol_id=uuid4(),
                target_symbol_id=uuid4(),
                relation="calls",
                depth=1,
            ),
        )

    return RepositoryChangeContext(
        repository_id=repository_id,
        task_description="Improve authentication",
        files=(
            ChangeContextFile(
                file_path="auth.py",
                reason="semantic repository match",
                relevance_score=0.95,
            ),
        ),
        symbols=(
            ChangeContextSymbol(
                symbol_id=uuid4(),
                file_path="auth.py",
                name="validate_token",
                symbol_type="function",
                start_line=10,
                end_line=20,
                reason="semantic repository match",
            ),
        ),
        dependencies=dependencies,
    )


@pytest.mark.asyncio
async def test_builds_planning_context() -> None:
    repository_id = uuid4()
    change_context = build_context(repository_id)

    service = PlanningContextService(
        change_context_service=FakeChangeContextService(change_context),
    )

    result = await service.build(
        repository_id=repository_id,
        task_description="Improve authentication",
    )

    assert result.repository_id == repository_id
    assert result.task_description == "Improve authentication"
    assert result.files == change_context.files
    assert result.symbols == change_context.symbols
    assert result.dependencies == change_context.dependencies


@pytest.mark.asyncio
async def test_build_adds_dependency_constraint() -> None:
    repository_id = uuid4()

    service = PlanningContextService(
        change_context_service=FakeChangeContextService(
            build_context(repository_id, include_dependencies=True),
        ),
    )

    result = await service.build(
        repository_id=repository_id,
        task_description="Improve authentication",
    )

    names = {constraint.name for constraint in result.constraints}

    assert "dependency_awareness" in names
    assert "relevant_files" in names
    assert "symbol_scope" in names
    assert "tests_required" in names


@pytest.mark.asyncio
async def test_build_adds_test_constraint_without_dependencies() -> None:
    repository_id = uuid4()

    service = PlanningContextService(
        change_context_service=FakeChangeContextService(
            build_context(repository_id, include_dependencies=False),
        ),
    )

    result = await service.build(
        repository_id=repository_id,
        task_description="Refactor authentication",
    )

    names = {constraint.name for constraint in result.constraints}

    assert "dependency_awareness" not in names
    assert "relevant_files" in names
    assert "symbol_scope" in names
    assert "tests_required" in names


@pytest.mark.asyncio
async def test_rejects_empty_task_description() -> None:
    repository_id = uuid4()

    service = PlanningContextService(
        change_context_service=FakeChangeContextService(
            build_context(repository_id),
        ),
    )

    with pytest.raises(PlanningContextError):
        await service.build(
            repository_id=repository_id,
            task_description="   ",
        )


@pytest.mark.asyncio
async def test_wraps_change_context_errors() -> None:
    repository_id = uuid4()

    service = PlanningContextService(
        change_context_service=FailingChangeContextService(),
    )

    with pytest.raises(PlanningContextError):
        await service.build(
            repository_id=repository_id,
            task_description="Improve authentication",
        )


def test_build_constraints_without_dependencies() -> None:
    repository_id = uuid4()
    context = build_context(
        repository_id,
        include_dependencies=False,
    )

    constraints = PlanningContextService._build_constraints(context)

    assert [constraint.name for constraint in constraints] == [
        "relevant_files",
        "symbol_scope",
        "tests_required",
    ]


def test_build_constraints_with_dependencies() -> None:
    repository_id = uuid4()
    context = build_context(
        repository_id,
        include_dependencies=True,
    )

    constraints = PlanningContextService._build_constraints(context)

    assert [constraint.name for constraint in constraints] == [
        "dependency_awareness",
        "relevant_files",
        "symbol_scope",
        "tests_required",
    ]
