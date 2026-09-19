from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ingestion.context.errors import ContextRetrievalError
from ingestion.context.models import (
    RepositoryContext,
    RepositoryContextFile,
    RepositoryContextItem,
)
from ingestion.retrieval.models import RetrievalResult


class RetrievalServiceProtocol(Protocol):
    """Protocol for retrieval services that return repository code."""

    async def search(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> list[RetrievalResult]: ...


class RepositoryContextService:
    """Build bounded, structured repository context from code retrieval."""

    DEFAULT_LIMIT = 10
    DEFAULT_MAX_CHARACTERS = 40_000

    def __init__(
        self,
        retrieval_service: RetrievalServiceProtocol,
        *,
        max_characters: int = DEFAULT_MAX_CHARACTERS,
    ) -> None:
        if max_characters <= 0:
            raise ValueError("max_characters must be greater than zero.")

        self._retrieval_service = retrieval_service
        self._max_characters = max_characters

    async def build_context(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = DEFAULT_LIMIT,
        max_characters: int | None = None,
    ) -> RepositoryContext:
        """Retrieve and assemble bounded repository context."""

        normalized_query = query.strip()

        if not normalized_query or limit <= 0:
            return RepositoryContext(
                repository_id=repository_id,
                query=query,
                items=(),
            )

        character_budget = (
            max_characters
            if max_characters is not None
            else self._max_characters
        )

        if character_budget <= 0:
            raise ValueError("max_characters must be greater than zero.")

        try:
            results = await self._retrieval_service.search(
                repository_id=repository_id,
                query=normalized_query,
                limit=limit,
            )
        except Exception as exc:
            raise ContextRetrievalError(
                "Failed to retrieve repository context."
            ) from exc

        items, truncated, character_count = self._assemble_items(
            results=results,
            max_characters=character_budget,
        )

        files = self._group_by_file(items)

        return RepositoryContext(
            repository_id=repository_id,
            query=normalized_query,
            items=items,
            files=files,
            total_candidates=len(results),
            truncated=truncated,
            character_count=character_count,
        )

    @classmethod
    def _assemble_items(
        cls,
        *,
        results: list[RetrievalResult],
        max_characters: int,
    ) -> tuple[tuple[RepositoryContextItem, ...], bool, int]:
        """Deduplicate and fit ranked results into the context budget."""

        selected: list[RepositoryContextItem] = []
        seen_chunk_ids: set[UUID] = set()
        character_count = 0
        truncated = False

        for result in results:
            if result.chunk_id in seen_chunk_ids:
                continue

            item = cls._to_context_item(result)
            item_characters = len(item.content)

            if character_count + item_characters <= max_characters:
                selected.append(item)
                seen_chunk_ids.add(result.chunk_id)
                character_count += item_characters
                continue

            truncated = True
            break

        if len(selected) < len(results):
            truncated = True

        return tuple(selected), truncated, character_count

    @staticmethod
    def _group_by_file(
        items: tuple[RepositoryContextItem, ...],
    ) -> tuple[RepositoryContextFile, ...]:
        """Group context items by file while preserving ranking order."""

        grouped: dict[str, list[RepositoryContextItem]] = {}

        for item in items:
            grouped.setdefault(item.file_path, []).append(item)

        files = [
            RepositoryContextFile(
                file_path=file_path,
                items=tuple(file_items),
                score=max(item.score for item in file_items),
            )
            for file_path, file_items in grouped.items()
        ]

        files.sort(
            key=lambda file: (
                -file.score,
                file.file_path,
            )
        )

        return tuple(files)

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
