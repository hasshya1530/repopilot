from uuid import uuid4

from ingestion.graph.models import SymbolRelation
from ingestion.graph.query.models import (
    DependencyQuery,
    DependencyResult,
    ImpactAnalysisResult,
    SymbolQuery,
    SymbolQueryResult,
)


def test_symbol_query_defaults_are_correct() -> None:
    query = SymbolQuery(name="validate_token")

    assert query.name == "validate_token"
    assert query.file_path is None
    assert query.symbol_type is None


def test_symbol_query_supports_filters() -> None:
    query = SymbolQuery(
        name="validate_token",
        file_path="auth.py",
        symbol_type="function",
    )

    assert query.name == "validate_token"
    assert query.file_path == "auth.py"
    assert query.symbol_type == "function"


def test_dependency_query_defaults_to_outgoing_depth_one() -> None:
    symbol_id = uuid4()

    query = DependencyQuery(symbol_id=symbol_id)

    assert query.symbol_id == symbol_id
    assert query.relation is None
    assert query.direction == "outgoing"
    assert query.max_depth == 1


def test_dependency_result_preserves_relationship() -> None:
    source = uuid4()
    target = uuid4()

    result = DependencyResult(
        source=source,
        target=target,
        relation=SymbolRelation.CALLS,
        depth=1,
    )

    assert result.source == source
    assert result.target == target
    assert result.relation is SymbolRelation.CALLS
    assert result.depth == 1


def test_symbol_query_result_contains_symbol_metadata() -> None:
    symbol_id = uuid4()

    result = SymbolQueryResult(
        symbol=symbol_id,
        file_path="auth.py",
        name="validate_token",
        symbol_type="function",
        start_line=10,
        end_line=20,
        parent=None,
    )

    assert result.symbol == symbol_id
    assert result.file_path == "auth.py"
    assert result.name == "validate_token"
    assert result.symbol_type == "function"
    assert result.start_line == 10
    assert result.end_line == 20
    assert result.parent is None


def test_impact_analysis_result_contains_affected_symbols_and_files() -> None:
    symbol_id = uuid4()
    affected_one = uuid4()
    affected_two = uuid4()

    result = ImpactAnalysisResult(
        symbol_id=symbol_id,
        affected_symbols=(affected_one, affected_two),
        affected_files=("auth.py", "api.py"),
        max_depth=3,
    )

    assert result.symbol_id == symbol_id
    assert result.affected_symbols == (affected_one, affected_two)
    assert result.affected_files == ("auth.py", "api.py")
    assert result.max_depth == 3
