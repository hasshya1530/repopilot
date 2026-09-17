from uuid import uuid4

from agents.planner.models import PlanningConstraint, PlanningContext
from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
)


def test_planning_constraint_contains_name_and_description() -> None:
    constraint = PlanningConstraint(
        name="backward_compatibility",
        description="Do not break existing API consumers.",
    )

    assert constraint.name == "backward_compatibility"
    assert constraint.description == "Do not break existing API consumers."


def test_planning_context_contains_repository_context() -> None:
    repository_id = uuid4()
    symbol_id = uuid4()
    source_id = uuid4()
    target_id = uuid4()

    files = (
        ChangeContextFile(
            file_path="auth.py",
            reason="semantic repository match",
            relevance_score=0.95,
        ),
    )

    symbols = (
        ChangeContextSymbol(
            symbol_id=symbol_id,
            file_path="auth.py",
            name="validate_token",
            symbol_type="function",
            start_line=10,
            end_line=20,
            reason="semantic repository match",
        ),
    )

    dependencies = (
        ChangeContextDependency(
            source_symbol_id=source_id,
            target_symbol_id=target_id,
            relation="calls",
            depth=1,
        ),
    )

    constraints = (
        PlanningConstraint(
            name="tests_required",
            description="All relevant tests must pass.",
        ),
    )

    context = PlanningContext(
        repository_id=repository_id,
        task_description="Improve token validation",
        files=files,
        symbols=symbols,
        dependencies=dependencies,
        constraints=constraints,
    )

    assert context.repository_id == repository_id
    assert context.task_description == "Improve token validation"
    assert context.files == files
    assert context.symbols == symbols
    assert context.dependencies == dependencies
    assert context.constraints == constraints


def test_planning_context_supports_empty_optional_collections() -> None:
    context = PlanningContext(
        repository_id=uuid4(),
        task_description="Refactor authentication",
        files=(),
        symbols=(),
        dependencies=(),
        constraints=(),
    )

    assert context.files == ()
    assert context.symbols == ()
    assert context.dependencies == ()
    assert context.constraints == ()
