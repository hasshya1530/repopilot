from uuid import uuid4

from ingestion.graph.models import (
    RepositoryGraph,
    RepositorySymbol,
)
from ingestion.graph.query.models import SymbolQuery
from ingestion.graph.query.service import SymbolQueryService


def build_graph() -> RepositoryGraph:
    auth_id = uuid4()
    refresh_id = uuid4()
    api_id = uuid4()

    return RepositoryGraph(
        repository_id=uuid4(),
        symbols=(
            RepositorySymbol(
                symbol_id=auth_id,
                file_path="auth.py",
                name="validate_token",
                symbol_type="function",
                start_line=10,
                end_line=20,
            ),
            RepositorySymbol(
                symbol_id=refresh_id,
                file_path="auth.py",
                name="refresh_token",
                symbol_type="function",
                start_line=22,
                end_line=30,
            ),
            RepositorySymbol(
                symbol_id=api_id,
                file_path="api.py",
                name="validate_token",
                symbol_type="function",
                start_line=5,
                end_line=12,
            ),
        ),
        edges=(),
    )


def test_find_symbols_by_name() -> None:
    service = SymbolQueryService(build_graph())

    results = service.find_symbols(
        SymbolQuery(name="validate_token"),
    )

    assert len(results) == 2
    assert {result.file_path for result in results} == {
        "auth.py",
        "api.py",
    }


def test_find_symbols_filters_by_file_path() -> None:
    service = SymbolQueryService(build_graph())

    results = service.find_symbols(
        SymbolQuery(
            name="validate_token",
            file_path="auth.py",
        ),
    )

    assert len(results) == 1
    assert results[0].file_path == "auth.py"
    assert results[0].name == "validate_token"


def test_find_symbols_filters_by_symbol_type() -> None:
    service = SymbolQueryService(build_graph())

    results = service.find_symbols(
        SymbolQuery(
            name="validate_token",
            symbol_type="class",
        ),
    )

    assert results == ()


def test_find_symbols_returns_empty_for_unknown_symbol() -> None:
    service = SymbolQueryService(build_graph())

    results = service.find_symbols(
        SymbolQuery(name="does_not_exist"),
    )

    assert results == ()


def test_find_symbols_returns_empty_for_blank_name() -> None:
    service = SymbolQueryService(build_graph())

    results = service.find_symbols(
        SymbolQuery(name="   "),
    )

    assert results == ()
