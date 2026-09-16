from collections import defaultdict
from typing import Protocol
from uuid import UUID

from ingestion.context.models import (
    RepositoryContext,
    RepositoryContextItem,
)
from ingestion.intelligence.models import (
    RepositoryFileSummary,
    RepositoryIntelligence,
)


class ContextServiceProtocol(Protocol):
    """Protocol for repository context services."""

    async def build_context(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> RepositoryContext: ...


class RepositoryIntelligenceService:
    """Aggregate retrieved repository context into file-level intelligence."""

    def __init__(
        self,
        context_service: ContextServiceProtocol,
    ) -> None:
        self._context_service = context_service

    async def analyze(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = 10,
    ) -> RepositoryIntelligence:
        """Build repository intelligence from relevant code context."""
        context = await self._context_service.build_context(
            repository_id=repository_id,
            query=query,
            limit=limit,
        )

        summaries = self._aggregate_files(context)

        return RepositoryIntelligence(
            repository_id=repository_id,
            query=query,
            files=summaries,
        )

    @staticmethod
    def _aggregate_files(
        context: RepositoryContext,
    ) -> tuple[RepositoryFileSummary, ...]:
        grouped: dict[str, list[RepositoryContextItem]] = defaultdict(list)

        for item in context.items:
            grouped[item.file_path].append(item)

        summaries: list[RepositoryFileSummary] = []

        for file_path, items in grouped.items():
            best_score = max(item.score for item in items)
            symbols = tuple(dict.fromkeys(item.symbol_name for item in items))

            summaries.append(
                RepositoryFileSummary(
                    file_path=file_path,
                    chunk_count=len(items),
                    best_score=best_score,
                    symbols=symbols,
                )
            )

        summaries.sort(
            key=lambda summary: summary.best_score,
            reverse=True,
        )

        return tuple(summaries)
