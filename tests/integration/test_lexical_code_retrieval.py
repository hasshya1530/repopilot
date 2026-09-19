from uuid import uuid4

import pytest

from apps.api.app.core.database import async_session_factory
from apps.api.app.models.code_chunk import CodeChunk as CodeChunkModel
from apps.api.app.models.repository import Repository
from ingestion.retrieval import CodeLexicalRetrievalService


async def create_repository() -> Repository:
    suffix = uuid4().hex[:8]

    return Repository(
        id=uuid4(),
        owner="repopilot-test",
        name=f"lexical-test-{suffix}",
        full_name=f"repopilot-test/lexical-test-{suffix}",
        github_repo_id=abs(uuid4().int) % 2_000_000_000,
        default_branch="main",
        description="Lexical retrieval integration test",
        is_private=True,
        clone_url="https://github.com/repopilot-test/lexical-test.git",
    )


@pytest.mark.asyncio
async def test_lexical_search_finds_exact_symbol_name() -> None:
    repository = await create_repository()

    matching_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="agents/jobs/worker.py",
        content="async def retry_job():\n    pass",
        symbol_name="retry_job",
        symbol_type="function",
        start_line=1,
        end_line=2,
        parent=None,
        commit_sha="lexical-test",
        content_hash="lexical-symbol-match",
        embedding=[1.0] + [0.0] * 767,
    )

    unrelated_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/math.py",
        content="def calculate_total():\n    pass",
        symbol_name="calculate_total",
        symbol_type="function",
        start_line=1,
        end_line=2,
        parent=None,
        commit_sha="lexical-test",
        content_hash="lexical-unrelated",
        embedding=[0.0, 1.0] + [0.0] * 766,
    )

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()
        session.add_all([matching_chunk, unrelated_chunk])
        await session.commit()

    async with async_session_factory() as session:
        service = CodeLexicalRetrievalService(session)

        results = await service.search(
            repository_id=repository.id,
            query="retry_job",
            limit=10,
        )

        assert len(results) == 1
        assert results[0].symbol_name == "retry_job"
        assert results[0].file_path == "agents/jobs/worker.py"
        assert results[0].score == 1.0

    async with async_session_factory() as session:
        stored_repository = await session.get(Repository, repository.id)
        assert stored_repository is not None
        await session.delete(stored_repository)
        await session.commit()


@pytest.mark.asyncio
async def test_lexical_search_finds_file_path_terms() -> None:
    repository = await create_repository()

    chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="agents/jobs/worker.py",
        content="Process background jobs.",
        symbol_name="process_job",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        commit_sha="lexical-path",
        content_hash="lexical-path-content",
        embedding=[1.0] + [0.0] * 767,
    )

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()
        session.add(chunk)
        await session.commit()

    async with async_session_factory() as session:
        service = CodeLexicalRetrievalService(session)

        results = await service.search(
            repository_id=repository.id,
            query="agents jobs worker",
            limit=10,
        )

        assert len(results) == 1
        assert results[0].file_path == "agents/jobs/worker.py"

    async with async_session_factory() as session:
        stored_repository = await session.get(Repository, repository.id)
        assert stored_repository is not None
        await session.delete(stored_repository)
        await session.commit()


@pytest.mark.asyncio
async def test_lexical_search_respects_commit_filter() -> None:
    repository = await create_repository()

    old_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/auth.py",
        content="authentication logic",
        symbol_name="authenticate",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        commit_sha="old",
        content_hash="lexical-old",
        embedding=[1.0] + [0.0] * 767,
    )

    new_chunk = CodeChunkModel(
        repository_id=repository.id,
        file_path="src/auth.py",
        content="authentication logic",
        symbol_name="authenticate",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        commit_sha="new",
        content_hash="lexical-new",
        embedding=[1.0] + [0.0] * 767,
    )

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()
        session.add_all([old_chunk, new_chunk])
        await session.commit()

    async with async_session_factory() as session:
        service = CodeLexicalRetrievalService(session)

        results = await service.search(
            repository_id=repository.id,
            query="authentication",
            commit_sha="new",
            limit=10,
        )

        assert len(results) == 1
        assert results[0].chunk_id == new_chunk.id

    async with async_session_factory() as session:
        stored_repository = await session.get(Repository, repository.id)
        assert stored_repository is not None
        await session.delete(stored_repository)
        await session.commit()


@pytest.mark.asyncio
async def test_lexical_search_returns_empty_for_blank_query() -> None:
    service = CodeLexicalRetrievalService(None)  # type: ignore[arg-type]

    results = await service.search(
        repository_id=uuid4(),
        query="   ",
    )

    assert results == []
