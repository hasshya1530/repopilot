from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.code_chunk import CodeChunk
from ingestion.retrieval.models import RetrievalResult


class CodeLexicalRetrievalService:
    """Retrieve repository code using PostgreSQL lexical matching."""

    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    _TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = DEFAULT_LIMIT,
        commit_sha: str | None = None,
    ) -> list[RetrievalResult]:
        """Return chunks matching important terms from a repository query."""

        normalized_query = query.strip()

        if not normalized_query or limit <= 0:
            return []

        effective_limit = min(limit, self.MAX_LIMIT)

        tokens = self._tokenize(normalized_query)

        if not tokens:
            return []

        conditions = [
            CodeChunk.repository_id == repository_id,
            CodeChunk.embedding.is_not(None),
        ]

        if commit_sha is not None and commit_sha.strip():
            conditions.append(CodeChunk.commit_sha == commit_sha.strip())

        lexical_conditions = []

        for token in tokens:
            pattern = f"%{token}%"

            lexical_conditions.extend(
                [
                    CodeChunk.file_path.ilike(pattern),
                    CodeChunk.symbol_name.ilike(pattern),
                    CodeChunk.content.ilike(pattern),
                ]
            )

        statement: Select[tuple[CodeChunk]] = (
            select(CodeChunk)
            .where(
                *conditions,
                or_(*lexical_conditions),
            )
            .order_by(
                CodeChunk.file_path.asc(),
                CodeChunk.start_line.asc(),
                CodeChunk.end_line.asc(),
                CodeChunk.id.asc(),
            )
            .limit(effective_limit)
        )

        result = await self._session.execute(statement)

        chunks = result.scalars().all()

        return [
            RetrievalResult(
                chunk_id=chunk.id,
                repository_id=chunk.repository_id,
                file_path=chunk.file_path,
                content=chunk.content,
                symbol_name=chunk.symbol_name,
                symbol_type=chunk.symbol_type,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                parent=chunk.parent,
                score=self._lexical_score(
                    tokens=tokens,
                    file_path=chunk.file_path,
                    symbol_name=chunk.symbol_name,
                    content=chunk.content,
                ),
            )
            for chunk in chunks
        ]

    @classmethod
    def _lexical_score(
        cls,
        *,
        tokens: set[str],
        file_path: str,
        symbol_name: str,
        content: str,
    ) -> float:
        if not tokens:
            return 0.0

        searchable_text = " ".join(
            (
                file_path,
                symbol_name,
                content,
            )
        ).lower()

        matched = sum(
            1
            for token in tokens
            if token.lower() in searchable_text
        )

        return matched / len(tokens)

    @classmethod
    def _tokenize(cls, value: str) -> set[str]:
        return {
            token.lower()
            for token in cls._TOKEN_PATTERN.findall(value)
            if len(token) > 1
        }
