from uuid import uuid4

from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
    RepositoryChangeContext,
)


def test_change_context_file_preserves_metadata() -> None:
    result = ChangeContextFile(
        file_path="auth.py",
        reason="Contains authentication logic",
        relevance_score=0.95,
    )

    assert result.file_path == "auth.py"
    assert result.reason == "Contains authentication logic"
    assert result.relevance_score == 0.95


def test_change_context_symbol_preserves_metadata() -> None:
    symbol_id = uuid4()

    result = ChangeContextSymbol(
        symbol_id=symbol_id,
        file_path="auth.py",
        name="validate_token",
        symbol_type="function",
        start_line=10,
        end_line=20,
        reason="Directly referenced by the requested change",
    )

    assert result.symbol_id == symbol_id
    assert result.file_path == "auth.py"
    assert result.name == "validate_token"
    assert result.symbol_type == "function"
    assert result.start_line == 10
    assert result.end_line == 20
    assert result.reason == "Directly referenced by the requested change"


def test_change_context_dependency_preserves_relationship() -> None:
    source = uuid4()
    target = uuid4()

    result = ChangeContextDependency(
        source_symbol_id=source,
        target_symbol_id=target,
        relation="calls",
        depth=2,
    )

    assert result.source_symbol_id == source
    assert result.target_symbol_id == target
    assert result.relation == "calls"
    assert result.depth == 2


def test_repository_change_context_preserves_all_context() -> None:
    repository_id = uuid4()
    symbol_id = uuid4()

    file_context = ChangeContextFile(
        file_path="auth.py",
        reason="Authentication implementation",
        relevance_score=0.9,
    )

    symbol_context = ChangeContextSymbol(
        symbol_id=symbol_id,
        file_path="auth.py",
        name="validate_token",
        symbol_type="function",
        start_line=10,
        end_line=20,
        reason="Authentication dependency",
    )

    dependency = ChangeContextDependency(
        source_symbol_id=uuid4(),
        target_symbol_id=symbol_id,
        relation="calls",
        depth=1,
    )

    result = RepositoryChangeContext(
        repository_id=repository_id,
        task_description="Improve authentication validation",
        files=(file_context,),
        symbols=(symbol_context,),
        dependencies=(dependency,),
    )

    assert result.repository_id == repository_id
    assert result.task_description == "Improve authentication validation"
    assert result.files == (file_context,)
    assert result.symbols == (symbol_context,)
    assert result.dependencies == (dependency,)
