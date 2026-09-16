from pathlib import Path
from uuid import uuid4

import pytest

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import async_session_factory
from apps.api.app.models.repository import Repository
from ingestion.context.service import RepositoryContextService
from ingestion.embeddings.factory import create_embedding_provider
from ingestion.indexing.service import RepositoryIndexingService
from ingestion.intelligence.service import RepositoryIntelligenceService
from ingestion.retrieval.service import CodeRetrievalService
from ingestion.services.embedding import EmbeddingService


@pytest.mark.asyncio
async def test_repository_intelligence_end_to_end(
    tmp_path: Path,
) -> None:
    repository_id = uuid4()
    repository_suffix = uuid4().hex[:8]

    repository = Repository(
        id=repository_id,
        owner="intelligence-test-owner",
        name=f"intelligence-test-{repository_suffix}",
        full_name=f"intelligence-test-owner/intelligence-test-{repository_suffix}",
        github_repo_id=abs(uuid4().int) % 2_000_000_000,
        default_branch="main",
        description="Repository intelligence integration test",
        is_private=True,
        clone_url="https://github.com/intelligence-test-owner/test.git",
    )

    (tmp_path / "auth.py").write_text(
        """
def refresh_access_token(refresh_token: str) -> str:
    return f"access:{refresh_token}"


def validate_access_token(token: str) -> bool:
    return token.startswith("access:")
""".strip()
        + "\n",
        encoding="utf-8",
    )

    settings = get_settings()
    embedding_provider = create_embedding_provider(settings)
    embedding_service = EmbeddingService(embedding_provider)

    async with async_session_factory() as session:
        session.add(repository)
        await session.commit()

    try:
        async with async_session_factory() as session:
            indexing_service = RepositoryIndexingService(
                session=session,
                embedding_service=embedding_service,
            )

            result = await indexing_service.index_repository(
                repository_id=repository_id,
                repository_path=tmp_path,
                commit_sha=f"intelligence-test-{repository_suffix}",
            )

            assert result.discovered_files == 1
            assert result.parsed_files == 1
            assert result.chunks_created == 3
            assert result.embeddings_created == 3

            await session.commit()

        async with async_session_factory() as session:
            retrieval_service = CodeRetrievalService(
                session=session,
                embedding_provider=embedding_provider,
            )

            context_service = RepositoryContextService(
                retrieval_service,
            )

            intelligence_service = RepositoryIntelligenceService(
                context_service,
            )

            intelligence = await intelligence_service.analyze(
                repository_id=repository_id,
                query="refresh access token authentication",
                limit=5,
            )

            assert intelligence.repository_id == repository_id
            assert intelligence.query == (
                "refresh access token authentication"
            )
            assert len(intelligence.files) > 0

            first_file = intelligence.files[0]

            assert first_file.file_path == "auth.py"
            assert first_file.chunk_count > 0
            assert 0.0 <= first_file.best_score <= 1.0
            assert "refresh_access_token" in first_file.symbols

    finally:
        async with async_session_factory() as session:
            stored_repository = await session.get(
                Repository,
                repository_id,
            )

            if stored_repository is not None:
                await session.delete(stored_repository)
                await session.commit()
