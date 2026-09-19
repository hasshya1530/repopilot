from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.workspace.git_service import GitService
from apps.api.app.core.config import Settings
from apps.api.app.models.code_chunk import CodeChunk
from ingestion.embeddings.factory import create_embedding_provider
from ingestion.indexing import IndexingResult, RepositoryIndexingService
from ingestion.services import EmbeddingService


class RepositoryIndexingApplicationService:
    """Application-level orchestration for repository indexing."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
    ) -> None:
        self._session = session
        self._settings = settings

    async def index_repository(
        self,
        *,
        repository_id: UUID,
        repository_path: Path,
    ) -> IndexingResult:
        """Index the current Git revision of a repository."""

        resolved_path = repository_path.resolve()

        git = GitService(resolved_path)
        commit_sha = git.current_commit()

        if not commit_sha:
            raise ValueError(
                f"Unable to determine Git commit for repository: {resolved_path}"
            )

        if await self._is_commit_indexed(
            repository_id=repository_id,
            commit_sha=commit_sha,
        ):
            return IndexingResult(
                discovered_files=0,
                parsed_files=0,
                chunks_created=0,
                embeddings_created=0,
            )

        embedding_provider = create_embedding_provider(self._settings)
        embedding_service = EmbeddingService(embedding_provider)

        indexing_service = RepositoryIndexingService(
            session=self._session,
            embedding_service=embedding_service,
        )

        try:
            result = await indexing_service.index_repository(
                repository_id=repository_id,
                repository_path=resolved_path,
                commit_sha=commit_sha,
            )

            await self._session.commit()

        except Exception:
            await self._session.rollback()
            raise

        return result

    async def _is_commit_indexed(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
    ) -> bool:
        statement = (
            select(CodeChunk.id)
            .where(
                CodeChunk.repository_id == repository_id,
                CodeChunk.commit_sha == commit_sha,
            )
            .limit(1)
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none() is not None


def create_repository_indexing_service(
    *,
    session: AsyncSession,
    settings: Settings,
) -> RepositoryIndexingApplicationService:
    """Create the configured repository indexing application service."""

    return RepositoryIndexingApplicationService(
        session=session,
        settings=settings,
    )
