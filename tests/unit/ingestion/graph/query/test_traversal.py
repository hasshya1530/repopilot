from uuid import uuid4

from ingestion.graph.models import RepositoryGraph, SymbolEdge, SymbolRelation
from ingestion.graph.query.models import DependencyQuery
from ingestion.graph.query.traversal import DependencyTraversalService


def test_outgoing_traversal_follows_multiple_depths() -> None:
    a = uuid4()
    b = uuid4()
    c = uuid4()

    graph = RepositoryGraph(
        repository_id=uuid4(),
        symbols=(),
        edges=(
            SymbolEdge(a, b, SymbolRelation.CALLS),
            SymbolEdge(b, c, SymbolRelation.CALLS),
        ),
    )

    service = DependencyTraversalService(graph)

    results = service.traverse(
        DependencyQuery(
            symbol_id=a,
            direction="outgoing",
            max_depth=2,
        )
    )

    assert len(results) == 2
    assert results[0].source == a
    assert results[0].target == b
    assert results[0].depth == 1
    assert results[1].source == b
    assert results[1].target == c
    assert results[1].depth == 2


def test_incoming_traversal_finds_dependants() -> None:
    a = uuid4()
    b = uuid4()
    c = uuid4()

    graph = RepositoryGraph(
        repository_id=uuid4(),
        symbols=(),
        edges=(
            SymbolEdge(a, b, SymbolRelation.CALLS),
            SymbolEdge(b, c, SymbolRelation.CALLS),
        ),
    )

    service = DependencyTraversalService(graph)

    results = service.traverse(
        DependencyQuery(
            symbol_id=c,
            direction="incoming",
            max_depth=2,
        )
    )

    assert len(results) == 2
    assert results[0].source == c
    assert results[0].target == b
    assert results[0].depth == 1
    assert results[1].source == b
    assert results[1].target == a
    assert results[1].depth == 2


def test_relation_filter_limits_traversal() -> None:
    a = uuid4()
    b = uuid4()
    c = uuid4()

    graph = RepositoryGraph(
        repository_id=uuid4(),
        symbols=(),
        edges=(
            SymbolEdge(a, b, SymbolRelation.CALLS),
            SymbolEdge(a, c, SymbolRelation.IMPORTS),
        ),
    )

    service = DependencyTraversalService(graph)

    results = service.traverse(
        DependencyQuery(
            symbol_id=a,
            relation=SymbolRelation.CALLS,
            max_depth=1,
        )
    )

    assert len(results) == 1
    assert results[0].target == b
    assert results[0].relation is SymbolRelation.CALLS


def test_depth_limit_stops_traversal() -> None:
    a = uuid4()
    b = uuid4()
    c = uuid4()

    graph = RepositoryGraph(
        repository_id=uuid4(),
        symbols=(),
        edges=(
            SymbolEdge(a, b, SymbolRelation.CALLS),
            SymbolEdge(b, c, SymbolRelation.CALLS),
        ),
    )

    service = DependencyTraversalService(graph)

    results = service.traverse(
        DependencyQuery(
            symbol_id=a,
            max_depth=1,
        )
    )

    assert len(results) == 1
    assert results[0].target == b


def test_zero_depth_returns_empty() -> None:
    a = uuid4()
    b = uuid4()

    graph = RepositoryGraph(
        repository_id=uuid4(),
        symbols=(),
        edges=(SymbolEdge(a, b, SymbolRelation.CALLS),),
    )

    service = DependencyTraversalService(graph)

    results = service.traverse(
        DependencyQuery(
            symbol_id=a,
            max_depth=0,
        )
    )

    assert results == ()


def test_unknown_symbol_returns_empty() -> None:
    graph = RepositoryGraph(
        repository_id=uuid4(),
        symbols=(),
        edges=(),
    )

    service = DependencyTraversalService(graph)

    results = service.traverse(
        DependencyQuery(
            symbol_id=uuid4(),
            max_depth=2,
        )
    )

    assert results == ()
