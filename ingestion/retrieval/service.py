from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.code_chunk import CodeChunk
from ingestion.embeddings.base import EmbeddingProvider
from ingestion.retrieval.models import RetrievalResult


class CodeRetrievalService:
    """Retrieve repository code using semantic vector similarity."""

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
        limit: int = 10,
    ) -> list[RetrievalResult]:
        """Return code chunks semantically relevant to a query."""

        if not query.strip():
            return []

        if limit <= 0:
            return []

        query_embedding = await self._embedding_provider.embed(query)

        distance = CodeChunk.embedding.cosine_distance(query_embedding)

        statement = (
            select(CodeChunk, distance.label("distance"))
            .where(
                CodeChunk.repository_id == repository_id,
                CodeChunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(limit)
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
                score=1.0 - float(distance_value),
            )
            for chunk, distance_value in rows
        ]
