from uuid import UUID, uuid4

from ingestion.graph.models import (
    RepositoryGraph,
    RepositorySymbol,
    SymbolEdge,
    SymbolRelation,
)
from ingestion.graph.query.impact import ImpactAnalysisService
from ingestion.graph.query.models import DependencyQuery
from ingestion.graph.query.traversal import DependencyTraversalService


def build_graph() -> tuple[RepositoryGraph, dict[str, UUID]]:
    auth_id = uuid4()
    service_id = uuid4()
    api_id = uuid4()

    graph = RepositoryGraph(
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
                symbol_id=service_id,
                file_path="services/auth.py",
                name="authenticate",
                symbol_type="function",
                start_line=5,
                end_line=15,
            ),
            RepositorySymbol(
                symbol_id=api_id,
                file_path="api/auth.py",
                name="login",
                symbol_type="function",
                start_line=20,
                end_line=30,
            ),
        ),
        edges=(
            SymbolEdge(
                service_id,
                auth_id,
                SymbolRelation.CALLS,
            ),
            SymbolEdge(
                api_id,
                service_id,
                SymbolRelation.CALLS,
            ),
        ),
    )

    return graph, {
        "auth": auth_id,
        "service": service_id,
        "api": api_id,
    }


def test_impact_analysis_finds_direct_dependant() -> None:
    graph, symbols = build_graph()
    traversal = DependencyTraversalService(graph)
    service = ImpactAnalysisService(graph, traversal)

    results = service.analyze(
        DependencyQuery(
            symbol_id=symbols["auth"],
            relation=SymbolRelation.CALLS,
            max_depth=1,
        )
    )

    assert results.symbol_id == symbols["auth"]
    assert results.affected_symbols == (symbols["service"],)
    assert results.affected_files == ("services/auth.py",)
    assert results.dependencies[0].source == symbols["auth"]
    assert results.dependencies[0].target == symbols["service"]
    assert results.dependencies[0].relation is SymbolRelation.CALLS
    assert results.dependencies[0].depth == 1
    assert results.max_depth == 1


def test_impact_analysis_follows_multiple_levels() -> None:
    graph, symbols = build_graph()
    traversal = DependencyTraversalService(graph)
    service = ImpactAnalysisService(graph, traversal)

    results = service.analyze(
        DependencyQuery(
            symbol_id=symbols["auth"],
            relation=SymbolRelation.CALLS,
            max_depth=2,
        )
    )

    assert results.affected_symbols == (
        symbols["service"],
        symbols["api"],
    )

    assert results.affected_files == (
        "services/auth.py",
        "api/auth.py",
    )

    assert len(results.dependencies) == 2

    assert results.dependencies[0].source == symbols["auth"]
    assert results.dependencies[0].target == symbols["service"]
    assert results.dependencies[0].relation is SymbolRelation.CALLS
    assert results.dependencies[0].depth == 1

    assert results.dependencies[1].source == symbols["service"]
    assert results.dependencies[1].target == symbols["api"]
    assert results.dependencies[1].relation is SymbolRelation.CALLS
    assert results.dependencies[1].depth == 2

    assert results.max_depth == 2


def test_impact_analysis_deduplicates_files() -> None:
    auth_id = uuid4()
    service_one_id = uuid4()
    service_two_id = uuid4()

    graph = RepositoryGraph(
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
                symbol_id=service_one_id,
                file_path="services/auth.py",
                name="authenticate",
                symbol_type="function",
                start_line=5,
                end_line=15,
            ),
            RepositorySymbol(
                symbol_id=service_two_id,
                file_path="services/auth.py",
                name="authorize",
                symbol_type="function",
                start_line=20,
                end_line=30,
            ),
        ),
        edges=(
            SymbolEdge(
                service_one_id,
                auth_id,
                SymbolRelation.CALLS,
            ),
            SymbolEdge(
                service_two_id,
                auth_id,
                SymbolRelation.CALLS,
            ),
        ),
    )

    traversal = DependencyTraversalService(graph)
    service = ImpactAnalysisService(graph, traversal)

    results = service.analyze(
        DependencyQuery(
            symbol_id=auth_id,
            relation=SymbolRelation.CALLS,
            max_depth=1,
        )
    )

    assert results.affected_symbols == (
        service_one_id,
        service_two_id,
    )
    assert results.affected_files == ("services/auth.py",)

    assert len(results.dependencies) == 2
    assert {dependency.target for dependency in results.dependencies} == {
        service_one_id,
        service_two_id,
    }

    assert all(dependency.source == auth_id for dependency in results.dependencies)

    assert all(dependency.relation is SymbolRelation.CALLS for dependency in results.dependencies)

    assert all(dependency.depth == 1 for dependency in results.dependencies)


def test_impact_analysis_returns_empty_for_unknown_symbol() -> None:
    graph, _ = build_graph()
    traversal = DependencyTraversalService(graph)
    service = ImpactAnalysisService(graph, traversal)

    results = service.analyze(
        DependencyQuery(
            symbol_id=uuid4(),
            max_depth=2,
        )
    )

    assert results.affected_symbols == ()
    assert results.affected_files == ()
    assert results.dependencies == ()
    assert results.max_depth == 2
