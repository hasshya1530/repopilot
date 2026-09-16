from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.api.app.core.database import async_session_factory
from apps.api.app.models.code_chunk import CodeChunk as CodeChunkModel
from apps.api.app.models.repository import Repository
from ingestion.chunker.models import CodeChunk
from ingestion.embeddings import OllamaEmbeddingProvider
from ingestion.parser.languages.base import SymbolType
from ingestion.services import (
    CodeChunkPersistenceService,
    EmbeddingService,
)


@pytest.mark.asyncio
async def test_real_embedding_is_persisted() -> None:
    repository_suffix = uuid4().hex[:8]

    repository = Repository(
        owner="repopilot-test",
        name=f"embedding-test-{repository_suffix}",
        full_name=f"repopilot-test/embedding-test-{repository_suffix}",
        github_repo_id=abs(uuid4().int) % 2_000_000_000,
        default_branch="main",
        description="Embedding persistence integration test",
        is_private=True,
        clone_url="https://github.com/repopilot-test/embedding-test.git",
    )

    chunk = CodeChunk(
        file_path="src/math.py",
        content=("def calculate_total(items):\n    return sum(items)"),
        symbol_name="calculate_total",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=2,
    )

    provider = OllamaEmbeddingProvider()
    embedding_service = EmbeddingService(provider)

    embedding = await embedding_service.embed_chunk(chunk)

    assert len(embedding) == 768
    assert all(isinstance(value, float) for value in embedding)

    async with async_session_factory() as session:
        session.add(repository)
        await session.flush()

        persistence_service = CodeChunkPersistenceService(session)

        db_chunk = await persistence_service.persist_chunk(
            repository_id=repository.id,
            commit_sha="test-commit-8-4",
            chunk=chunk,
            embedding=embedding,
            content_hash="test-content-hash-8-4",
        )

        await session.commit()

        chunk_id = db_chunk.id
        repository_id = repository.id

    async with async_session_factory() as session:
        result = await session.execute(select(CodeChunkModel).where(CodeChunkModel.id == chunk_id))
        stored_chunk = result.scalar_one()

        assert stored_chunk.repository_id == repository_id
        assert stored_chunk.file_path == "src/math.py"
        assert stored_chunk.symbol_name == "calculate_total"
        assert stored_chunk.symbol_type == "function"
        assert stored_chunk.embedding is not None
        assert len(stored_chunk.embedding) == 768

        await session.delete(stored_chunk)
        await session.commit()

    async with async_session_factory() as session:
        result = await session.execute(select(Repository).where(Repository.id == repository_id))
        stored_repository = result.scalar_one()

        await session.delete(stored_repository)
        await session.commit()


@pytest.mark.asyncio
async def test_real_embedding_batch() -> None:
    chunks = [
        CodeChunk(
            file_path="src/math.py",
            content="def add(a, b):\n    return a + b",
            symbol_name="add",
            symbol_type=SymbolType.FUNCTION,
            start_line=1,
            end_line=2,
        ),
        CodeChunk(
            file_path="src/math.py",
            content="def subtract(a, b):\n    return a - b",
            symbol_name="subtract",
            symbol_type=SymbolType.FUNCTION,
            start_line=4,
            end_line=5,
        ),
    ]

    provider = OllamaEmbeddingProvider()
    service = EmbeddingService(provider)

    embeddings = await service.embed_chunks(chunks)

    assert len(embeddings) == 2
    assert all(len(embedding) == 768 for embedding in embeddings)
    assert all(isinstance(value, float) for embedding in embeddings for value in embedding)
