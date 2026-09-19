from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from apps.api.app.core.config import get_settings
from apps.api.app.models.code_chunk import CodeChunk
from apps.api.app.models.repository import Repository
from apps.api.app.services.repository_indexing import (
    create_repository_indexing_service,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index a RepoPilot repository into the semantic code store."
    )

    parser.add_argument(
        "--repository",
        required=True,
        help="Repository full name.",
    )
    parser.add_argument(
        "--path",
        required=True,
        type=Path,
        help="Local repository checkout to index.",
    )
    parser.add_argument(
        "--repository-id",
        required=True,
        type=UUID,
        help="Repository UUID in the target database.",
    )

    return parser.parse_args()


def create_session_factory() -> async_sessionmaker[AsyncSession]:
    settings = get_settings()

    if os.getenv("REPOPILOT_TEST_DB") == "1":
        database_url = settings.test_database_url
        database_name = "repopilot_test"
    else:
        database_url = settings.database_url
        database_name = "repopilot"

    print(f"Database target: {database_name}")

    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
    )

    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def main() -> None:
    args = parse_args()

    repository_path = args.path.resolve()

    if not repository_path.exists():
        raise RuntimeError(
            f"Repository path does not exist: {repository_path}"
        )

    if not repository_path.is_dir():
        raise RuntimeError(
            f"Repository path is not a directory: {repository_path}"
        )

    session_factory = create_session_factory()

    async with session_factory() as session:
        repository = await session.get(
            Repository,
            args.repository_id,
        )

        if repository is None:
            raise RuntimeError(
                f"Repository not found for id: {args.repository_id}"
            )

        if repository.full_name != args.repository:
            raise RuntimeError(
                "Repository identity mismatch: "
                f"database has {repository.full_name!r}, "
                f"but CLI requested {args.repository!r}"
            )

        print(f"Repository: {repository.full_name}")
        print(f"Repository ID: {repository.id}")
        print(f"Path: {repository_path}")

        service = create_repository_indexing_service(
            session=session,
            settings=get_settings(),
        )

        result = await service.index_repository(
            repository_id=repository.id,
            repository_path=repository_path,
        )

        print()
        print("Indexing complete")
        print(f"  discovered_files:    {result.discovered_files}")
        print(f"  parsed_files:        {result.parsed_files}")
        print(f"  chunks_created:      {result.chunks_created}")
        print(f"  embeddings_created:  {result.embeddings_created}")

        chunk_count_result = await session.execute(
            select(CodeChunk.id).where(
                CodeChunk.repository_id == repository.id,
            )
        )

        total_chunks = len(chunk_count_result.scalars().all())

        print()
        print(f"Total stored chunks for repository: {total_chunks}")


if __name__ == "__main__":
    asyncio.run(main())
