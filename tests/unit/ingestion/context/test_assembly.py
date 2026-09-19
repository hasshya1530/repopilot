from uuid import uuid4

import pytest

from ingestion.context.service import RepositoryContextService
from ingestion.retrieval.models import RetrievalResult


class FakeRetrievalService:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results

    async def search(self, **kwargs):
        return self.results


def make_result(
    *,
    file_path: str,
    symbol_name: str,
    content: str,
    score: float,
):
    return RetrievalResult(
        chunk_id=uuid4(),
        repository_id=uuid4(),
        file_path=file_path,
        content=content,
        symbol_name=symbol_name,
        symbol_type="function",
        start_line=1,
        end_line=5,
        parent=None,
        score=score,
    )


@pytest.mark.asyncio
async def test_context_assembles_retrieval_results() -> None:
    repository_id = uuid4()

    first = make_result(
        file_path="agents/jobs/worker.py",
        symbol_name="run",
        content="def run():\n    pass",
        score=0.95,
    )

    second = make_result(
        file_path="agents/jobs/retry.py",
        symbol_name="retry",
        content="def retry():\n    pass",
        score=0.85,
    )

    service = RepositoryContextService(
        FakeRetrievalService([first, second]),
    )

    context = await service.build_context(
        repository_id=repository_id,
        query="background job retry",
        limit=10,
    )

    assert context.repository_id == repository_id
    assert context.query == "background job retry"
    assert len(context.items) == 2
    assert len(context.files) == 2
    assert context.total_candidates == 2
    assert context.truncated is False
    assert context.character_count > 0


@pytest.mark.asyncio
async def test_context_groups_chunks_by_file() -> None:
    repository_id = uuid4()

    first = make_result(
        file_path="agents/jobs/worker.py",
        symbol_name="run",
        content="def run():\n    pass",
        score=0.90,
    )

    second = make_result(
        file_path="agents/jobs/worker.py",
        symbol_name="stop",
        content="def stop():\n    pass",
        score=0.80,
    )

    third = make_result(
        file_path="agents/jobs/retry.py",
        symbol_name="retry",
        content="def retry():\n    pass",
        score=0.85,
    )

    service = RepositoryContextService(
        FakeRetrievalService([first, second, third]),
    )

    context = await service.build_context(
        repository_id=repository_id,
        query="background jobs",
    )

    assert len(context.files) == 2
    assert context.files[0].file_path == "agents/jobs/worker.py"
    assert len(context.files[0].items) == 2
    assert context.files[0].score == 0.90


@pytest.mark.asyncio
async def test_context_respects_character_budget() -> None:
    repository_id = uuid4()

    first = make_result(
        file_path="src/first.py",
        symbol_name="first",
        content="a" * 100,
        score=0.95,
    )

    second = make_result(
        file_path="src/second.py",
        symbol_name="second",
        content="b" * 100,
        score=0.85,
    )

    service = RepositoryContextService(
        FakeRetrievalService([first, second]),
    )

    context = await service.build_context(
        repository_id=repository_id,
        query="test",
        max_characters=180,
    )

    assert len(context.items) == 1
    assert context.truncated is True
    assert context.total_candidates == 2
    assert context.character_count <= 180


@pytest.mark.asyncio
async def test_context_deduplicates_chunks() -> None:
    repository_id = uuid4()
    shared_id = uuid4()

    first = RetrievalResult(
        chunk_id=shared_id,
        repository_id=repository_id,
        file_path="src/auth.py",
        content="authenticate()",
        symbol_name="authenticate",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        score=0.95,
    )

    duplicate = RetrievalResult(
        chunk_id=shared_id,
        repository_id=repository_id,
        file_path="src/auth.py",
        content="authenticate()",
        symbol_name="authenticate",
        symbol_type="function",
        start_line=1,
        end_line=1,
        parent=None,
        score=0.90,
    )

    service = RepositoryContextService(
        FakeRetrievalService([first, duplicate]),
    )

    context = await service.build_context(
        repository_id=repository_id,
        query="authentication",
    )

    assert len(context.items) == 1
    assert context.total_candidates == 2
    assert context.truncated is True


@pytest.mark.asyncio
async def test_blank_query_returns_empty_context() -> None:
    repository_id = uuid4()

    service = RepositoryContextService(
        FakeRetrievalService([]),
    )

    context = await service.build_context(
        repository_id=repository_id,
        query="   ",
    )

    assert context.items == ()
    assert context.files == ()
    assert context.truncated is False


@pytest.mark.asyncio
async def test_non_positive_limit_returns_empty_context() -> None:
    repository_id = uuid4()

    service = RepositoryContextService(
        FakeRetrievalService([]),
    )

    context = await service.build_context(
        repository_id=repository_id,
        query="authentication",
        limit=0,
    )

    assert context.items == ()


def test_invalid_context_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_characters"):
        RepositoryContextService(
            FakeRetrievalService([]),
            max_characters=0,
        )


@pytest.mark.asyncio
async def test_invalid_runtime_context_budget_is_rejected() -> None:
    service = RepositoryContextService(
        FakeRetrievalService([]),
    )

    with pytest.raises(ValueError, match="max_characters"):
        await service.build_context(
            repository_id=uuid4(),
            query="authentication",
            max_characters=0,
        )


@pytest.mark.asyncio
async def test_retrieval_errors_are_wrapped() -> None:
    class FailingRetrievalService:
        async def search(self, **kwargs):
            raise RuntimeError("database unavailable")

    service = RepositoryContextService(
        FailingRetrievalService(),
    )

    from ingestion.context.errors import ContextRetrievalError

    with pytest.raises(ContextRetrievalError, match="Failed to retrieve"):
        await service.build_context(
            repository_id=uuid4(),
            query="authentication",
        )
