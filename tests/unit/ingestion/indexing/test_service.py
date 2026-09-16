from pathlib import Path
from uuid import UUID, uuid4

import pytest

from ingestion.chunker.models import CodeChunk
from ingestion.indexing.models import IndexingResult
from ingestion.indexing.service import RepositoryIndexingService
from ingestion.parser.files import RepositoryFile
from ingestion.parser.languages.base import SymbolType


class FakeEmbeddingService:
    def __init__(self) -> None:
        self.received_chunks: list[CodeChunk] = []

    async def embed_chunks(
        self,
        chunks: list[CodeChunk],
    ) -> list[list[float]]:
        self.received_chunks = chunks
        return [[0.1, 0.2] for _ in chunks]


class FakeChunker:
    def __init__(
        self,
        chunks_by_file: dict[str, list[CodeChunk]],
    ) -> None:
        self._chunks_by_file = chunks_by_file

    def chunk_file(
        self,
        repository_file: RepositoryFile,
    ) -> list[CodeChunk]:
        return self._chunks_by_file.get(
            repository_file.relative_path,
            [],
        )


class FakePersistenceService:
    def __init__(self) -> None:
        self.persisted: list[dict[str, object]] = []

    async def persist_chunk(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
        chunk: CodeChunk,
        embedding: list[float],
        content_hash: str,
    ) -> None:
        self.persisted.append(
            {
                "repository_id": repository_id,
                "commit_sha": commit_sha,
                "chunk": chunk,
                "embedding": embedding,
                "content_hash": content_hash,
            }
        )


@pytest.mark.asyncio
async def test_index_repository_indexes_chunks(tmp_path: Path) -> None:
    source_file = tmp_path / "auth.py"
    source_file.write_text(
        "def refresh_token():\n    return True\n",
        encoding="utf-8",
    )

    repository_id = uuid4()

    chunk = CodeChunk(
        file_path="auth.py",
        content="def refresh_token():\n    return True",
        symbol_name="refresh_token",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=2,
        parent=None,
    )

    embedding_service = FakeEmbeddingService()
    chunker = FakeChunker(
        {
            "auth.py": [chunk],
        }
    )
    persistence_service = FakePersistenceService()

    service = RepositoryIndexingService(
        session=None,
        embedding_service=embedding_service,
        chunker=chunker,
        persistence_service=persistence_service,
    )

    result = await service.index_repository(
        repository_id=repository_id,
        repository_path=tmp_path,
        commit_sha="abc123",
    )

    assert isinstance(result, IndexingResult)
    assert result.discovered_files == 1
    assert result.parsed_files == 1
    assert result.chunks_created == 1
    assert result.embeddings_created == 1

    assert len(embedding_service.received_chunks) == 1
    assert len(persistence_service.persisted) == 1

    persisted = persistence_service.persisted[0]

    assert persisted["repository_id"] == repository_id
    assert persisted["commit_sha"] == "abc123"
    assert persisted["chunk"] == chunk
    assert persisted["embedding"] == [0.1, 0.2]
    assert persisted["content_hash"]


@pytest.mark.asyncio
async def test_index_repository_handles_empty_repository(
    tmp_path: Path,
) -> None:
    embedding_service = FakeEmbeddingService()
    persistence_service = FakePersistenceService()

    service = RepositoryIndexingService(
        session=None,
        embedding_service=embedding_service,
        persistence_service=persistence_service,
    )

    result = await service.index_repository(
        repository_id=uuid4(),
        repository_path=tmp_path,
        commit_sha="abc123",
    )

    assert result.discovered_files == 0
    assert result.parsed_files == 0
    assert result.chunks_created == 0
    assert result.embeddings_created == 0

    assert embedding_service.received_chunks == []
    assert persistence_service.persisted == []


@pytest.mark.asyncio
async def test_index_repository_ignores_unsupported_files(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "notes.txt"
    source_file.write_text(
        "This is documentation.",
        encoding="utf-8",
    )

    embedding_service = FakeEmbeddingService()
    persistence_service = FakePersistenceService()

    service = RepositoryIndexingService(
        session=None,
        embedding_service=embedding_service,
        persistence_service=persistence_service,
    )

    result = await service.index_repository(
        repository_id=uuid4(),
        repository_path=tmp_path,
        commit_sha="abc123",
    )

    assert result.discovered_files == 1
    assert result.parsed_files == 0
    assert result.chunks_created == 0
    assert result.embeddings_created == 0

    assert persistence_service.persisted == []
