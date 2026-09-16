from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import async_session_factory
from apps.api.app.models.code_chunk import CodeChunk as CodeChunkModel
from apps.api.app.models.repository import Repository
from ingestion.context.service import RepositoryContextService
from ingestion.embeddings.factory import create_embedding_provider
from ingestion.indexing.service import RepositoryIndexingService
from ingestion.retrieval.service import CodeRetrievalService
from ingestion.services.embedding import EmbeddingService


@pytest.mark.asyncio
async def test_repository_context_end_to_end(
    tmp_path: Path,
) -> None:
    repository_name = f"repository-{uuid4().hex[:8]}"
    repository_id = uuid4()

    repository = Repository(
        id=repository_id,
        owner="context-test-owner",
        name=repository_name,
        full_name=f"context-test-owner/{repository_name}",
        github_repo_id=abs(uuid4().int) % 2_000_000_000,
        default_branch="main",
        clone_url="https://github.com/context-test-owner/test.git",
    )

    (tmp_path / "auth.py").write_text(
        '''
def refresh_access_token(refresh_token: str) -> str:
    """Create a new access token from a refresh token."""
    return f"access:{refresh_token}"


def validate_access_token(token: str) -> bool:
    """Validate an access token."""
    return token.startswith("access:")
'''.strip()
        + "\n",
        encoding="utf-8",
    )

    settings = get_settings()
    embedding_provider = create_embedding_provider(settings)
    embedding_service = EmbeddingService(embedding_provider)

    async with async_session_factory() as session:
        session.add(repository)
        await session.commit()

    async with async_session_factory() as session:
        indexing_service = RepositoryIndexingService(
            session,
            embedding_service,
        )

        result = await indexing_service.index_repository(
            repository_id=repository_id,
            repository_path=tmp_path,
            commit_sha="context-test-sha",
        )

        assert result.discovered_files == 1
        assert result.parsed_files == 1
        assert result.chunks_created == 3
        assert result.embeddings_created == 3

        await session.commit()

    async with async_session_factory() as session:
        retrieval_service = CodeRetrievalService(
            session,
            embedding_provider,
        )

        context_service = RepositoryContextService(
            retrieval_service,
        )

        context = await context_service.build_context(
            repository_id=repository_id,
            query="refresh access token",
            limit=5,
        )

        assert context.repository_id == repository_id
        assert context.query == "refresh access token"
        assert len(context.items) > 0

        file_paths = {item.file_path for item in context.items}
        symbol_names = {item.symbol_name for item in context.items}

        assert "auth.py" in file_paths
        assert "refresh_access_token" in symbol_names

        assert all(item.content.strip() for item in context.items)
        assert all(0.0 <= item.score <= 1.0 for item in context.items)

        stored_chunks = await session.execute(
            select(CodeChunkModel).where(
                CodeChunkModel.repository_id == repository_id,
            )
        )

        assert len(stored_chunks.scalars().all()) == 3

    async with async_session_factory() as session:
        stored_repository = await session.get(
            Repository,
            repository_id,
        )

        assert stored_repository is not None

        await session.delete(stored_repository)
        await session.commit()
