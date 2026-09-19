from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.chunker.code import CodeChunker
from ingestion.chunker.models import CodeChunk
from ingestion.indexing.errors import IndexingFileError
from ingestion.indexing.models import IndexingResult
from ingestion.parser.discovery import DiscoveryConfig, discover_files
from ingestion.parser.files import RepositoryFile
from ingestion.parser.worker_client import ParserWorkerClient
from ingestion.services.code_chunk_persistence import CodeChunkPersistenceService


class ChunkerProtocol(Protocol):
    def chunk_file(self, repository_file: RepositoryFile) -> list[CodeChunk]:
        """Chunk a repository file."""
        ...


class EmbeddingServiceProtocol(Protocol):
    async def embed_chunks(self, chunks: list[CodeChunk]) -> list[list[float]]:
        """Generate embeddings for code chunks."""
        ...


class PersistenceServiceProtocol(Protocol):
    async def persist_chunk(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
        chunk: CodeChunk,
        embedding: list[float],
        content_hash: str,
    ) -> object:
        """Persist a chunk and its embedding."""
        ...


class RepositoryIndexingService:
    """Discover, parse, chunk, embed, and persist a repository."""

    def __init__(
        self,
        session: AsyncSession | None,
        embedding_service: EmbeddingServiceProtocol,
        *,
        chunker: ChunkerProtocol | None = None,
        persistence_service: PersistenceServiceProtocol | None = None,
        discovery_config: DiscoveryConfig | None = None,
        embedding_batch_size: int = 16,
    ) -> None:
        if embedding_batch_size <= 0:
            raise ValueError("embedding_batch_size must be greater than zero.")

        self._session = session
        self._embedding_service = embedding_service
        self._chunker = chunker
        self._persistence_service = persistence_service
        self._discovery_config = discovery_config or DiscoveryConfig()
        self._embedding_batch_size = embedding_batch_size

        if self._persistence_service is None and session is not None:
            self._persistence_service = CodeChunkPersistenceService(session)

        if self._persistence_service is None:
            raise ValueError(
                "A persistence service or AsyncSession is required for repository indexing."
            )

    async def index_repository(
        self,
        *,
        repository_id: UUID,
        repository_path: Path,
        commit_sha: str = "working-tree",
    ) -> IndexingResult:
        """Index all supported files in a repository."""

        files = discover_files(
            repository_path,
            config=self._discovery_config,
        )

        worker: ParserWorkerClient | None = None

        if self._chunker is None:
            worker = ParserWorkerClient()
            chunker: ChunkerProtocol = CodeChunker(parser_worker=worker)
        else:
            chunker = self._chunker

        chunks: list[CodeChunk] = []
        parsed_files = 0

        try:
            for repository_file in files:
                try:
                    file_chunks = chunker.chunk_file(repository_file)
                except (OSError, UnicodeDecodeError) as exc:
                    raise IndexingFileError(
                        f"Failed to index {repository_file.relative_path}: {exc}"
                    ) from exc

                if file_chunks:
                    parsed_files += 1
                    chunks.extend(file_chunks)
        finally:
            if worker is not None:
                worker.close()

        if not chunks:
            return IndexingResult(
                discovered_files=len(files),
                parsed_files=parsed_files,
                chunks_created=0,
                embeddings_created=0,
            )

        persistence_service = self._persistence_service

        if persistence_service is None:
            raise RuntimeError(
                "Persistence service is unavailable after initialization."
            )

        embeddings_created = 0

        total_batches = (
            len(chunks) + self._embedding_batch_size - 1
        ) // self._embedding_batch_size

        for batch_number, start in enumerate(
            range(0, len(chunks), self._embedding_batch_size),
            start=1,
        ):
            batch = chunks[
                start : start + self._embedding_batch_size
            ]

            embeddings = await self._embedding_service.embed_chunks(batch)

            if len(embeddings) != len(batch):
                raise RuntimeError(
                    "Embedding service returned an unexpected number of embeddings: "
                    f"expected {len(batch)}, got {len(embeddings)}."
                )

            for chunk, embedding in zip(batch, embeddings, strict=True):
                content_hash = sha256(
                    chunk.content.encode("utf-8")
                ).hexdigest()

                await persistence_service.persist_chunk(
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    chunk=chunk,
                    embedding=embedding,
                    content_hash=content_hash,
                )

            embeddings_created += len(batch)

            if self._session is not None:
                await self._session.commit()

            print(
                f"[indexing] batch {batch_number}/{total_batches} "
                f"persisted {len(batch)} chunks "
                f"({embeddings_created}/{len(chunks)})",
                flush=True,
            )

        return IndexingResult(
            discovered_files=len(files),
            parsed_files=parsed_files,
            chunks_created=len(chunks),
            embeddings_created=embeddings_created,
        )
