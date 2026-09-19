from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.api.app.core.database import async_session_factory
from apps.api.app.models.code_chunk import CodeChunk as CodeChunkModel
from apps.api.app.models.repository import Repository
from ingestion.embeddings.base import EmbeddingProvider
from ingestion.retrieval import CodeRetrievalService


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Deterministic provider for testing vector retrieval."""

    @property
    def model_name(self) -> str:
        return "deterministic-test-model"

    @property
    def dimension(self) -> int:
        return 768

    async def embed(self, text: str) -> list[float]:
        if "authentication" in text.lower():
            return [1.0] + [0.0] * 767

        return [0.0, 1.0] + [0.0] * 766


async def create_test_repository(repository_suffix: str) -> Repository:
    return Repository(
        id=uuid4(),
        owner="repopilot-test",
        name=f"retrieval-test-{repository_suffix}",
        full_name=f"repopilot-test/retrieval-test-{repository_suffix}",
        github_repo_id=abs(uuid4().int) % 2_000_000_000,
        default_branch="main",
        description="Vector retrieval integration test",
        is_private=True,
        clone_url="https://github.com/repopilot-test/retrieval-test.git",
    )


async def delete_repository(repository_id) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = result.scalar_one()

        await session.delete(repository)
        await session.commit()


@pytest.mark.asyncio
async def test_vector_search_ranks_similar_chunk_first() -> None:
    repository_suffix = uuid4().hex[:8]
    repository = await create_test_repository(repository_suffix)

    authentication_embedding = [1.0] + [0.0] * 767
    unrelated_embedding = [0.0, 1.0] + [0.0] * 766

    authentication_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/auth.py",
        content="def refresh_access_token():\n    return refresh_token()",
        symbol_name="refresh_access_token",
        symbol_type="function",
        start_line=1,
        end_line=2,
        parent=None,
        commit_sha="test-retrieval-8-5",
        content_hash="auth-content-hash",
        embedding=authentication_embedding,
    )

    unrelated_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/math.py",
        content="def calculate_total(items):\n    return sum(items)",
        symbol_name="calculate_total",
        symbol_type="function",
        start_line=1,
        end_line=2,
        parent=None,
        commit_sha="test-retrieval-8-5",
        content_hash="math-content-hash",
        embedding=unrelated_embedding,
    )

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()

        session.add_all(
            [
                authentication_chunk,
                unrelated_chunk,
            ]
        )

        await session.commit()

    async with async_session_factory() as session:
        service = CodeRetrievalService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(),
        )

        results = await service.search(
            repository_id=repository.id,
            query="  authentication token refresh  ",
            limit=2,
        )

        assert len(results) == 2

        assert results[0].file_path == "src/auth.py"
        assert results[0].symbol_name == "refresh_access_token"

        assert results[1].file_path == "src/math.py"
        assert results[1].symbol_name == "calculate_total"

        assert results[0].score > results[1].score

    await delete_repository(repository.id)


@pytest.mark.asyncio
async def test_vector_search_filters_by_commit_sha() -> None:
    repository = await create_test_repository(uuid4().hex[:8])

    embedding = [1.0] + [0.0] * 767

    old_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/auth.py",
        content="old authentication implementation",
        symbol_name="old_auth",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        commit_sha="old-commit",
        content_hash="old-content-hash",
        embedding=embedding,
    )

    new_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/auth.py",
        content="new authentication implementation",
        symbol_name="new_auth",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        commit_sha="new-commit",
        content_hash="new-content-hash",
        embedding=embedding,
    )

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()
        session.add_all([old_chunk, new_chunk])
        await session.commit()

    async with async_session_factory() as session:
        service = CodeRetrievalService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(),
        )

        results = await service.search(
            repository_id=repository.id,
            query="authentication",
            limit=10,
            commit_sha="new-commit",
        )

        assert len(results) == 1
        assert results[0].symbol_name == "new_auth"

    await delete_repository(repository.id)


@pytest.mark.asyncio
async def test_vector_search_filters_by_minimum_score() -> None:
    repository = await create_test_repository(uuid4().hex[:8])

    matching_embedding = [1.0] + [0.0] * 767
    unrelated_embedding = [0.0, 1.0] + [0.0] * 766

    matching_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/auth.py",
        content="authentication implementation",
        symbol_name="authenticate",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        commit_sha="score-test",
        content_hash="score-auth-content",
        embedding=matching_embedding,
    )

    unrelated_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/math.py",
        content="math implementation",
        symbol_name="calculate",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        commit_sha="score-test",
        content_hash="score-math-content",
        embedding=unrelated_embedding,
    )

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()
        session.add_all([matching_chunk, unrelated_chunk])
        await session.commit()

    async with async_session_factory() as session:
        service = CodeRetrievalService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(),
        )

        results = await service.search(
            repository_id=repository.id,
            query="authentication",
            limit=10,
            min_score=0.5,
        )

        assert len(results) == 1
        assert results[0].file_path == "src/auth.py"
        assert results[0].score >= 0.5

    await delete_repository(repository.id)


@pytest.mark.asyncio
async def test_vector_search_caps_large_limit() -> None:
    repository = await create_test_repository(uuid4().hex[:8])

    chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/auth.py",
        content="authentication implementation",
        symbol_name="authenticate",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        commit_sha="limit-test",
        content_hash="limit-content-hash",
        embedding=[1.0] + [0.0] * 767,
    )

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()
        session.add(chunk)
        await session.commit()

    async with async_session_factory() as session:
        service = CodeRetrievalService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(),
        )

        results = await service.search(
            repository_id=repository.id,
            query="authentication",
            limit=10_000,
        )

        assert len(results) == 1

    await delete_repository(repository.id)


@pytest.mark.asyncio
async def test_vector_search_returns_empty_for_blank_query() -> None:
    service = CodeRetrievalService(
        session=None,  # type: ignore[arg-type]
        embedding_provider=DeterministicEmbeddingProvider(),
    )

    results = await service.search(
        repository_id=uuid4(),
        query="   ",
    )

    assert results == []


@pytest.mark.asyncio
async def test_vector_search_returns_empty_for_non_positive_limit() -> None:
    service = CodeRetrievalService(
        session=None,  # type: ignore[arg-type]
        embedding_provider=DeterministicEmbeddingProvider(),
    )

    results = await service.search(
        repository_id=uuid4(),
        query="authentication",
        limit=0,
    )

    assert results == []


@pytest.mark.asyncio
async def test_vector_search_rejects_invalid_minimum_score() -> None:
    service = CodeRetrievalService(
        session=None,  # type: ignore[arg-type]
        embedding_provider=DeterministicEmbeddingProvider(),
    )

    with pytest.raises(ValueError, match="min_score"):
        await service.search(
            repository_id=uuid4(),
            query="authentication",
            min_score=1.5,
        )
