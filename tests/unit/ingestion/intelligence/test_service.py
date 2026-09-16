from uuid import UUID, uuid4

import pytest

from ingestion.context.models import RepositoryContext, RepositoryContextItem
from ingestion.intelligence.service import RepositoryIntelligenceService


class FakeContextService:
    def __init__(self, context: RepositoryContext) -> None:
        self.context = context

    async def build_context(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int,
    ) -> RepositoryContext:
        return self.context


@pytest.mark.asyncio
async def test_analyze_aggregates_chunks_by_file() -> None:
    repository_id = uuid4()

    context = RepositoryContext(
        repository_id=repository_id,
        query="authentication",
        items=(
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/auth.py",
                symbol_name="login",
                symbol_type="function",
                start_line=1,
                end_line=5,
                content="def login(): pass",
                score=0.91,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/auth.py",
                symbol_name="validate_token",
                symbol_type="function",
                start_line=8,
                end_line=12,
                content="def validate_token(): pass",
                score=0.87,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/users.py",
                symbol_name="get_user",
                symbol_type="function",
                start_line=1,
                end_line=4,
                content="def get_user(): pass",
                score=0.72,
            ),
        ),
    )

    service = RepositoryIntelligenceService(
        FakeContextService(context),
    )

    intelligence = await service.analyze(
        repository_id=repository_id,
        query="authentication",
        limit=10,
    )

    assert intelligence.repository_id == repository_id
    assert intelligence.query == "authentication"
    assert len(intelligence.files) == 2

    assert intelligence.files[0].file_path == "src/auth.py"
    assert intelligence.files[0].chunk_count == 2
    assert intelligence.files[0].best_score == 0.91
    assert intelligence.files[0].symbols == (
        "login",
        "validate_token",
    )

    assert intelligence.files[1].file_path == "src/users.py"
    assert intelligence.files[1].chunk_count == 1
    assert intelligence.files[1].best_score == 0.72


@pytest.mark.asyncio
async def test_analyze_returns_empty_files_for_empty_context() -> None:
    repository_id = uuid4()

    context = RepositoryContext(
        repository_id=repository_id,
        query="authentication",
        items=(),
    )

    service = RepositoryIntelligenceService(
        FakeContextService(context),
    )

    intelligence = await service.analyze(
        repository_id=repository_id,
        query="authentication",
    )

    assert intelligence.repository_id == repository_id
    assert intelligence.files == ()


@pytest.mark.asyncio
async def test_analyze_preserves_first_symbol_occurrence() -> None:
    repository_id = uuid4()

    context = RepositoryContext(
        repository_id=repository_id,
        query="authentication",
        items=(
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/auth.py",
                symbol_name="login",
                symbol_type="function",
                start_line=1,
                end_line=5,
                content="login",
                score=0.8,
            ),
            RepositoryContextItem(
                chunk_id=uuid4(),
                file_path="src/auth.py",
                symbol_name="login",
                symbol_type="function",
                start_line=7,
                end_line=11,
                content="login",
                score=0.7,
            ),
        ),
    )

    service = RepositoryIntelligenceService(
        FakeContextService(context),
    )

    intelligence = await service.analyze(
        repository_id=repository_id,
        query="authentication",
    )

    assert intelligence.files[0].symbols == ("login",)
