from uuid import uuid4

import pytest

from ingestion.retrieval.hybrid import HybridCodeRetrievalService
from ingestion.retrieval.models import RetrievalResult


def make_result(
    *,
    file_path: str,
    symbol_name: str,
    score: float,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        repository_id=uuid4(),
        file_path=file_path,
        content=f"Implementation for {symbol_name}",
        symbol_name=symbol_name,
        symbol_type="function",
        start_line=1,
        end_line=5,
        parent=None,
        score=score,
    )


class FakeSemanticService:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results

    async def search(self, **kwargs):
        return self.results


class FakeLexicalService:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results

    async def search(self, **kwargs):
        return self.results


@pytest.mark.asyncio
async def test_hybrid_retrieval_merges_and_ranks_candidates() -> None:
    repository_id = uuid4()

    semantic = make_result(
        file_path="src/semantic.py",
        symbol_name="semantic_match",
        score=0.90,
    )

    lexical = make_result(
        file_path="src/retry.py",
        symbol_name="retry_job",
        score=1.0,
    )

    service = HybridCodeRetrievalService(
        semantic_service=FakeSemanticService([semantic]),
        lexical_service=FakeLexicalService([lexical]),
    )

    results = await service.search(
        repository_id=repository_id,
        query="retry_job",
        limit=2,
    )

    assert len(results) == 2
    assert results[0].result.symbol_name == "retry_job"


@pytest.mark.asyncio
async def test_hybrid_retrieval_deduplicates_same_chunk() -> None:
    shared_chunk = make_result(
        file_path="src/retry.py",
        symbol_name="retry_job",
        score=0.90,
    )

    service = HybridCodeRetrievalService(
        semantic_service=FakeSemanticService([shared_chunk]),
        lexical_service=FakeLexicalService([shared_chunk]),
    )

    results = await service.search(
        repository_id=shared_chunk.repository_id,
        query="retry_job",
        limit=10,
    )

    assert len(results) == 1
    assert results[0].result.chunk_id == shared_chunk.chunk_id


@pytest.mark.asyncio
async def test_hybrid_retrieval_respects_limit() -> None:
    candidates = [
        make_result(
            file_path=f"src/file_{index}.py",
            symbol_name=f"function_{index}",
            score=0.90 - index * 0.01,
        )
        for index in range(5)
    ]

    service = HybridCodeRetrievalService(
        semantic_service=FakeSemanticService(candidates),
        lexical_service=FakeLexicalService([]),
    )

    results = await service.search(
        repository_id=candidates[0].repository_id,
        query="function",
        limit=2,
    )

    assert len(results) == 2


@pytest.mark.asyncio
async def test_hybrid_retrieval_returns_empty_for_blank_query() -> None:
    service = HybridCodeRetrievalService(
        semantic_service=FakeSemanticService([]),
        lexical_service=FakeLexicalService([]),
    )

    results = await service.search(
        repository_id=uuid4(),
        query="   ",
        limit=10,
    )

    assert results == []


def test_merge_candidates_deduplicates_by_chunk_id() -> None:
    shared = make_result(
        file_path="src/shared.py",
        symbol_name="shared",
        score=0.8,
    )

    semantic_only = make_result(
        file_path="src/semantic.py",
        symbol_name="semantic",
        score=0.7,
    )

    lexical_only = make_result(
        file_path="src/lexical.py",
        symbol_name="lexical",
        score=0.9,
    )

    merged = HybridCodeRetrievalService._merge_candidates(
        [shared, semantic_only],
        [shared, lexical_only],
    )

    assert len(merged) == 3
    assert {item.chunk_id for item in merged} == {
        shared.chunk_id,
        semantic_only.chunk_id,
        lexical_only.chunk_id,
    }
