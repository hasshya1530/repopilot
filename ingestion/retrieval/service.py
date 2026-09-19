from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.code_chunk import CodeChunk
from ingestion.embeddings.base import EmbeddingProvider
from ingestion.retrieval.models import RetrievalResult


class CodeRetrievalService:
    """Retrieve repository code using semantic vector similarity."""

    DEFAULT_LIMIT = 10
    MAX_LIMIT = 100

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._session = session
        self._embedding_provider = embedding_provider

    async def search(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = DEFAULT_LIMIT,
        commit_sha: str | None = None,
        min_score: float | None = None,
    ) -> list[RetrievalResult]:
        """Return code chunks semantically relevant to a repository query.

        Results are ranked by cosine similarity between the query embedding
        and stored code-chunk embeddings.

        Args:
            repository_id: Repository whose indexed chunks should be searched.
            query: Natural-language search query.
            limit: Maximum number of results to return.
            commit_sha: Optional indexed commit/version filter.
            min_score: Optional minimum cosine-similarity score in [-1, 1].
        """

        normalized_query = query.strip()

        if not normalized_query:
            return []

        if limit <= 0:
            return []

        effective_limit = min(limit, self.MAX_LIMIT)

        normalized_commit_sha = (
            commit_sha.strip()
            if commit_sha is not None
            else None
        )

        if normalized_commit_sha == "":
            normalized_commit_sha = None

        if min_score is not None and not -1.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between -1.0 and 1.0.")

        query_embedding = await self._embedding_provider.embed(normalized_query)

        distance = CodeChunk.embedding.cosine_distance(query_embedding)
        similarity = (1.0 - distance).label("similarity")

        conditions = [
            CodeChunk.repository_id == repository_id,
            CodeChunk.embedding.is_not(None),
        ]

        if normalized_commit_sha is not None:
            conditions.append(CodeChunk.commit_sha == normalized_commit_sha)

        if min_score is not None:
            conditions.append(similarity >= min_score)

        statement = (
            select(CodeChunk, similarity)
            .where(*conditions)
            .order_by(
                distance.asc(),
                CodeChunk.file_path.asc(),
                CodeChunk.start_line.asc(),
                CodeChunk.end_line.asc(),
                CodeChunk.id.asc(),
            )
            .limit(effective_limit)
        )

        result = await self._session.execute(statement)

        rows = result.all()

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
                score=float(score),
            )
            for chunk, score in rows
        ]
