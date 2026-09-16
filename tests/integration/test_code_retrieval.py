from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.api.app.core.database import async_session_factory
from apps.api.app.models.code_chunk import CodeChunk
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


@pytest.mark.asyncio
async def test_vector_search_ranks_similar_chunk_first() -> None:
    repository_suffix = uuid4().hex[:8]
    repository_id = uuid4()

    authentication_embedding = [1.0] + [0.0] * 767
    unrelated_embedding = [0.0, 1.0] + [0.0] * 766

    repository = Repository(
        id=repository_id,
        owner="repopilot-test",
        name=f"retrieval-test-{repository_suffix}",
        full_name=f"repopilot-test/retrieval-test-{repository_suffix}",
        github_repo_id=abs(uuid4().int) % 2_000_000_000,
        default_branch="main",
        description="Vector retrieval integration test",
        is_private=True,
        clone_url="https://github.com/repopilot-test/retrieval-test.git",
    )

    authentication_chunk = CodeChunk(
        repository_id=repository_id,
        file_path="src/auth.py",
        content=("def refresh_access_token():\n    return refresh_token()"),
        symbol_name="refresh_access_token",
        symbol_type="function",
        start_line=1,
        end_line=2,
        parent=None,
        commit_sha="test-retrieval-8-5",
        content_hash="auth-content-hash",
        embedding=authentication_embedding,
    )

    unrelated_chunk = CodeChunk(
        repository_id=repository_id,
        file_path="src/math.py",
        content=("def calculate_total(items):\n    return sum(items)"),
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
            repository_id=repository_id,
            query="authentication token refresh",
            limit=2,
        )

        assert len(results) == 2

        assert results[0].file_path == "src/auth.py"
        assert results[0].symbol_name == "refresh_access_token"

        assert results[1].file_path == "src/math.py"
        assert results[1].symbol_name == "calculate_total"

        assert results[0].score > results[1].score

    async with async_session_factory() as session:
        result = await session.execute(select(Repository).where(Repository.id == repository_id))
        stored_repository = result.scalar_one()

        await session.delete(stored_repository)
        await session.commit()
