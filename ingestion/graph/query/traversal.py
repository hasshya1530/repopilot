from collections import defaultdict, deque

from ingestion.graph.models import RepositoryGraph, SymbolEdge, SymbolRelation
from ingestion.graph.query.models import DependencyQuery, DependencyResult


class DependencyTraversalService:
    """Traverse repository symbol dependencies."""

    def __init__(self, graph: RepositoryGraph) -> None:
        self._graph = graph
        self._outgoing = self._build_index(
            graph.edges,
            reverse=False,
        )
        self._incoming = self._build_index(
            graph.edges,
            reverse=True,
        )

    def traverse(
        self,
        query: DependencyQuery,
    ) -> tuple[DependencyResult, ...]:
        """Traverse dependencies from a starting symbol."""

        if query.max_depth < 1:
            return ()

        if query.direction not in {"outgoing", "incoming"}:
            return ()

        adjacency = self._outgoing if query.direction == "outgoing" else self._incoming

        queue: deque[tuple[object, int]] = deque([(query.symbol_id, 0)])
        visited: set[tuple[object, object, SymbolRelation]] = set()
        results: list[DependencyResult] = []

        while queue:
            current_id, current_depth = queue.popleft()

            if current_depth >= query.max_depth:
                continue

            for edge in adjacency.get(current_id, ()):
                if query.relation is not None and edge.relation != query.relation:
                    continue

                edge_key = (edge.source, edge.target, edge.relation)

                if edge_key in visited:
                    continue

                visited.add(edge_key)

                if query.direction == "outgoing":
                    source = edge.source
                    target = edge.target
                else:
                    source = edge.target
                    target = edge.source

                depth = current_depth + 1

                results.append(
                    DependencyResult(
                        source=source,
                        target=target,
                        relation=edge.relation,
                        depth=depth,
                    )
                )

                queue.append((target, depth))

        return tuple(results)

    @staticmethod
    def _build_index(
        edges: tuple[SymbolEdge, ...],
        *,
        reverse: bool,
    ) -> dict[object, tuple[SymbolEdge, ...]]:
        index: defaultdict[object, list[SymbolEdge]] = defaultdict(list)

        for edge in edges:
            key = edge.target if reverse else edge.source
            index[key].append(edge)

        return {key: tuple(value) for key, value in index.items()}
