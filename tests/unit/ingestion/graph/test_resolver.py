from uuid import uuid4

from ingestion.graph.models import RepositorySymbol, SymbolRelation, SymbolRelationship
from ingestion.graph.resolver import SymbolResolver


def test_resolver_resolves_same_file_call() -> None:
    login_id = uuid4()
    validate_id = uuid4()

    symbols = [
        RepositorySymbol(
            symbol_id=login_id,
            file_path="src/auth.py",
            name="login",
            symbol_type="function",
            start_line=1,
            end_line=3,
        ),
        RepositorySymbol(
            symbol_id=validate_id,
            file_path="src/auth.py",
            name="validate_token",
            symbol_type="function",
            start_line=5,
            end_line=7,
        ),
    ]

    relationship = SymbolRelationship(
        source_name="login",
        target_name="validate_token",
        relation=SymbolRelation.CALLS,
        source_file="src/auth.py",
    )

    resolver = SymbolResolver(symbols)

    assert resolver.resolve(relationship) == (login_id, validate_id)


def test_resolver_resolves_import_using_target_file() -> None:
    module_id = uuid4()
    path_id = uuid4()

    symbols = [
        RepositorySymbol(
            symbol_id=module_id,
            file_path="src/client.py",
            name="__module__",
            symbol_type="module",
            start_line=1,
            end_line=5,
        ),
        RepositorySymbol(
            symbol_id=path_id,
            file_path="pathlib",
            name="Path",
            symbol_type="class",
            start_line=1,
            end_line=1,
        ),
    ]

    relationship = SymbolRelationship(
        source_name="__module__",
        target_name="Path",
        relation=SymbolRelation.IMPORTS,
        source_file="src/client.py",
        target_file="pathlib",
    )

    resolver = SymbolResolver(symbols)

    assert resolver.resolve(relationship) == (module_id, path_id)


def test_resolver_returns_none_for_unknown_target() -> None:
    source_id = uuid4()

    symbols = [
        RepositorySymbol(
            symbol_id=source_id,
            file_path="src/auth.py",
            name="login",
            symbol_type="function",
            start_line=1,
            end_line=3,
        )
    ]

    relationship = SymbolRelationship(
        source_name="login",
        target_name="missing_function",
        relation=SymbolRelation.CALLS,
        source_file="src/auth.py",
    )

    resolver = SymbolResolver(symbols)

    assert resolver.resolve(relationship) is None


def test_resolver_returns_none_for_unknown_source() -> None:
    target_id = uuid4()

    symbols = [
        RepositorySymbol(
            symbol_id=target_id,
            file_path="src/auth.py",
            name="validate_token",
            symbol_type="function",
            start_line=5,
            end_line=7,
        )
    ]

    relationship = SymbolRelationship(
        source_name="missing_function",
        target_name="validate_token",
        relation=SymbolRelation.CALLS,
        source_file="src/auth.py",
    )

    resolver = SymbolResolver(symbols)

    assert resolver.resolve(relationship) is None
