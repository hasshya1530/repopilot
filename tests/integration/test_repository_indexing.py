from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.api.app.core.database import async_session_factory
from apps.api.app.models.code_chunk import CodeChunk as CodeChunkModel
from apps.api.app.models.repository import Repository
from ingestion.embeddings import OllamaEmbeddingProvider
from ingestion.indexing import RepositoryIndexingService
from ingestion.services import EmbeddingService


@pytest.mark.asyncio
async def test_index_repository_end_to_end(tmp_path: Path) -> None:
    auth_file = tmp_path / "auth.py"
    auth_file.write_text(
        """
def refresh_access_token(refresh_token: str) -> str:
    \"\"\"Generate a new access token from a refresh token.\"\"\"
    return f"access:{refresh_token}"
""".strip(),
        encoding="utf-8",
    )

    payments_file = tmp_path / "payments.py"
    payments_file.write_text(
        """
def calculate_invoice_total(items: list[float]) -> float:
    \"\"\"Calculate the total invoice amount.\"\"\"
    return sum(items)
""".strip(),
        encoding="utf-8",
    )

    repository_id = uuid4()

    embedding_provider = OllamaEmbeddingProvider()
    embedding_service = EmbeddingService(embedding_provider)

    async with async_session_factory() as session:
        test_repo_name = f"test-repository-{uuid4().hex[:8]}"

        repository = Repository(
            id=repository_id,
            owner="test-owner",
            name=test_repo_name,
            full_name=f"test-owner/{test_repo_name}",
            github_repo_id=uuid4().int % 2_000_000_000,
            default_branch="main",
            clone_url="https://github.com/test-owner/test-repository.git",
            is_private=False,
        )

        session.add(repository)
        await session.commit()

        service = RepositoryIndexingService(
            session=session,
            embedding_service=embedding_service,
        )

        result = await service.index_repository(
            repository_id=repository_id,
            repository_path=tmp_path,
            commit_sha="integration-test-sha",
        )

        assert result.discovered_files == 2
        assert result.parsed_files == 2
        assert result.chunks_created == 4
        assert result.embeddings_created == 4

        query = await session.execute(
            select(CodeChunkModel)
            .where(
                CodeChunkModel.repository_id == repository_id,
            )
            .order_by(CodeChunkModel.file_path)
        )

        chunks = query.scalars().all()

        assert len(chunks) == 4

        chunk_symbols = {(chunk.file_path, chunk.symbol_name) for chunk in chunks}

        assert chunk_symbols == {
            ("auth.py", "module"),
            ("auth.py", "refresh_access_token"),
            ("payments.py", "module"),
            ("payments.py", "calculate_invoice_total"),
        }

        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 768
            assert chunk.commit_sha == "integration-test-sha"

        await session.delete(repository)
        await session.commit()


@pytest.mark.asyncio
async def test_index_repository_rejects_duplicate_commit_index(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "auth.py"
    source_file.write_text(
        """
def refresh_access_token(refresh_token: str) -> str:
    return f"access:{refresh_token}"
""".strip(),
        encoding="utf-8",
    )

    repository_id = uuid4()
    test_repo_name = f"test-repository-{uuid4().hex[:8]}"

    embedding_provider = OllamaEmbeddingProvider()
    embedding_service = EmbeddingService(embedding_provider)

    async with async_session_factory() as session:
        repository = Repository(
            id=repository_id,
            owner="test-owner",
            name=test_repo_name,
            full_name=f"test-owner/{test_repo_name}",
            github_repo_id=uuid4().int % 2_000_000_000,
            default_branch="main",
            clone_url="https://github.com/test-owner/test-repository.git",
            is_private=False,
        )

        session.add(repository)
        await session.commit()

        service = RepositoryIndexingService(
            session=session,
            embedding_service=embedding_service,
        )

        await service.index_repository(
            repository_id=repository_id,
            repository_path=tmp_path,
            commit_sha="duplicate-test-sha",
        )

        with pytest.raises(IntegrityError):
            await service.index_repository(
                repository_id=repository_id,
                repository_path=tmp_path,
                commit_sha="duplicate-test-sha",
            )

        await session.rollback()

        await session.delete(repository)
        await session.commit()
