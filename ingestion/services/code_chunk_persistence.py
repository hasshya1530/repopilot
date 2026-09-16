from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.code_chunk import CodeChunk as CodeChunkModel
from ingestion.chunker.models import CodeChunk


class CodeChunkPersistenceService:
    """Persist ingested code chunks and their embeddings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_chunk(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
        chunk: CodeChunk,
        embedding: list[float],
        content_hash: str,
    ) -> CodeChunkModel:
        """Persist a code chunk together with its embedding."""

        db_chunk = CodeChunkModel(
            repository_id=repository_id,
            file_path=chunk.file_path,
            content=chunk.content,
            symbol_name=chunk.symbol_name,
            symbol_type=chunk.symbol_type.value,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            parent=chunk.parent,
            commit_sha=commit_sha,
            content_hash=content_hash,
            embedding=embedding,
        )

        self._session.add(db_chunk)
        await self._session.flush()

        return db_chunk
