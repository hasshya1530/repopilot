from typing import Protocol
from uuid import UUID

from ingestion.context.errors import ContextRetrievalError
from ingestion.context.models import RepositoryContext, RepositoryContextItem
from ingestion.retrieval.models import RetrievalResult


class RetrievalServiceProtocol(Protocol):
    """Protocol for semantic code retrieval services."""

    async def search(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> list[RetrievalResult]: ...


class RepositoryContextService:
    """Build structured repository context from semantic code retrieval."""

    def __init__(
        self,
        retrieval_service: RetrievalServiceProtocol,
    ) -> None:
        self._retrieval_service = retrieval_service

    async def build_context(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = 10,
    ) -> RepositoryContext:
        """Retrieve relevant code and assemble repository context."""

        if not query.strip():
            return RepositoryContext(
                repository_id=repository_id,
                query=query,
                items=(),
            )

        if limit <= 0:
            return RepositoryContext(
                repository_id=repository_id,
                query=query,
                items=(),
            )

        try:
            results = await self._retrieval_service.search(
                repository_id=repository_id,
                query=query,
                limit=limit,
            )
        except Exception as exc:
            raise ContextRetrievalError("Failed to retrieve repository context.") from exc

        items = tuple(self._to_context_item(result) for result in results)

        return RepositoryContext(
            repository_id=repository_id,
            query=query,
            items=items,
        )

    @staticmethod
    def _to_context_item(
        result: RetrievalResult,
    ) -> RepositoryContextItem:
        return RepositoryContextItem(
            chunk_id=result.chunk_id,
            file_path=result.file_path,
            symbol_name=result.symbol_name,
            symbol_type=result.symbol_type,
            start_line=result.start_line,
            end_line=result.end_line,
            content=result.content,
            score=result.score,
            parent=result.parent,
        )
