from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.api.app.core.database import async_session_factory
from apps.api.app.models.repository import Repository
from ingestion.chunker.models import CodeChunk
from ingestion.embeddings import OllamaEmbeddingProvider
from ingestion.parser.languages.base import SymbolType
from ingestion.retrieval import CodeRetrievalService
from ingestion.services import (
    CodeChunkPersistenceService,
    EmbeddingService,
)


@pytest.mark.asyncio
async def test_real_semantic_code_retrieval() -> None:
    repository_id = uuid4()
    repository_suffix = uuid4().hex[:8]

    repository = Repository(
        id=repository_id,
        owner="repopilot-test",
        name=f"semantic-test-{repository_suffix}",
        full_name=f"repopilot-test/semantic-test-{repository_suffix}",
        github_repo_id=abs(uuid4().int) % 2_000_000_000,
        default_branch="main",
        description="Real semantic retrieval integration test",
        is_private=True,
        clone_url="https://github.com/repopilot-test/semantic-test.git",
    )

    chunks = [
        CodeChunk(
            file_path="src/auth.py",
            content=(
                "def refresh_access_token(refresh_token):\n"
                "    if not refresh_token:\n"
                "        raise ValueError('Missing refresh token')\n"
                "    return issue_new_access_token(refresh_token)"
            ),
            symbol_name="refresh_access_token",
            symbol_type=SymbolType.FUNCTION,
            start_line=1,
            end_line=4,
        ),
        CodeChunk(
            file_path="src/payments.py",
            content=(
                "def calculate_invoice_total(items):\n    return sum(item.price for item in items)"
            ),
            symbol_name="calculate_invoice_total",
            symbol_type=SymbolType.FUNCTION,
            start_line=1,
            end_line=2,
        ),
    ]

    provider = OllamaEmbeddingProvider()
    embedding_service = EmbeddingService(provider)

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()

        persistence_service = CodeChunkPersistenceService(session)

        for index, chunk in enumerate(chunks):
            embedding = await embedding_service.embed_chunk(chunk)

            await persistence_service.persist_chunk(
                repository_id=repository_id,
                commit_sha="test-semantic-retrieval-8-5",
                chunk=chunk,
                embedding=embedding,
                content_hash=f"semantic-content-hash-{index}",
            )

        await session.commit()

    async with async_session_factory() as session:
        retrieval_service = CodeRetrievalService(
            session=session,
            embedding_provider=provider,
        )

        results = await retrieval_service.search(
            repository_id=repository_id,
            query=(
                "The application cannot refresh an expired access token using the refresh token."
            ),
            limit=2,
        )

        assert len(results) == 2

        assert results[0].file_path == "src/auth.py"
        assert results[0].symbol_name == "refresh_access_token"

        assert results[0].score > results[1].score

    async with async_session_factory() as session:
        result = await session.execute(select(Repository).where(Repository.id == repository_id))
        stored_repository = result.scalar_one()

        await session.delete(stored_repository)
        await session.commit()
