from hashlib import sha256
from pathlib import Path
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.chunker.code import CodeChunker
from ingestion.chunker.models import CodeChunk
from ingestion.indexing.errors import IndexingFileError
from ingestion.indexing.models import IndexingResult
from ingestion.parser.discovery import (
    DiscoveryConfig,
    discover_files,
)
from ingestion.parser.files import RepositoryFile
from ingestion.services.code_chunk_persistence import CodeChunkPersistenceService


class ChunkerProtocol(Protocol):
    """Protocol for repository code chunkers."""

    def chunk_file(self, repository_file: RepositoryFile) -> list[CodeChunk]: ...


class EmbeddingServiceProtocol(Protocol):
    """Protocol for services that generate embeddings."""

    async def embed_chunks(
        self,
        chunks: list[CodeChunk],
    ) -> list[list[float]]: ...


class PersistenceServiceProtocol(Protocol):
    """Protocol for persisting indexed code chunks."""

    async def persist_chunk(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
        chunk: CodeChunk,
        embedding: list[float],
        content_hash: str,
    ) -> object: ...


class RepositoryIndexingService:
    """Index repository source code into the semantic code store."""

    def __init__(
        self,
        session: AsyncSession | None,
        embedding_service: EmbeddingServiceProtocol,
        *,
        chunker: ChunkerProtocol | None = None,
        persistence_service: PersistenceServiceProtocol | None = None,
        discovery_config: DiscoveryConfig | None = None,
    ) -> None:
        self._embedding_service = embedding_service
        self._chunker = chunker or CodeChunker()

        if persistence_service is not None:
            self._persistence_service = persistence_service
        elif session is not None:
            self._persistence_service = CodeChunkPersistenceService(session)
        else:
            raise ValueError("session is required when persistence_service is not provided")

        self._discovery_config = discovery_config

    async def index_repository(
        self,
        *,
        repository_id: UUID,
        repository_path: Path,
        commit_sha: str,
    ) -> IndexingResult:
        """Discover, parse, embed, and persist repository code."""

        files = discover_files(
            repository_path,
            self._discovery_config,
        )

        chunks: list[CodeChunk] = []

        for repository_file in files:
            try:
                file_chunks = self._chunker.chunk_file(repository_file)
            except (OSError, UnicodeDecodeError) as exc:
                raise IndexingFileError(
                    f"Failed to process repository file: {repository_file.relative_path}"
                ) from exc

            chunks.extend(file_chunks)

        if not chunks:
            return IndexingResult(
                discovered_files=len(files),
                parsed_files=0,
                chunks_created=0,
                embeddings_created=0,
            )

        embeddings = await self._embedding_service.embed_chunks(chunks)

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            content_hash = self._content_hash(chunk.content)

            await self._persistence_service.persist_chunk(
                repository_id=repository_id,
                commit_sha=commit_sha,
                chunk=chunk,
                embedding=embedding,
                content_hash=content_hash,
            )

        parsed_files = len({chunk.file_path for chunk in chunks})

        return IndexingResult(
            discovered_files=len(files),
            parsed_files=parsed_files,
            chunks_created=len(chunks),
            embeddings_created=len(embeddings),
        )

    @staticmethod
    def _content_hash(content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()
