from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.orchestrator.adapters.repository_source import LocalRepositorySource


@pytest.mark.asyncio
async def test_prepare_returns_configured_repository_path(
    tmp_path: Path,
) -> None:
    repository_path = tmp_path / "repo"
    repository_path.mkdir()

    source = LocalRepositorySource(
        {"example/repo": repository_path},
    )

    repository = SimpleNamespace(
        full_name="example/repo",
    )

    result = await source.prepare(repository)  # type: ignore[arg-type]

    assert result == repository_path.resolve()


@pytest.mark.asyncio
async def test_prepare_rejects_unknown_repository() -> None:
    source = LocalRepositorySource({})

    repository = SimpleNamespace(
        full_name="example/missing",
    )

    with pytest.raises(FileNotFoundError, match="No local checkout"):
        await source.prepare(repository)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_prepare_rejects_missing_path(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing"

    source = LocalRepositorySource(
        {"example/repo": missing_path},
    )

    repository = SimpleNamespace(
        full_name="example/repo",
    )

    with pytest.raises(
        FileNotFoundError,
        match="Local repository checkout does not exist",
    ):
        await source.prepare(repository)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_prepare_rejects_file(
    tmp_path: Path,
) -> None:
    repository_path = tmp_path / "repo"
    repository_path.write_text("not a directory")

    source = LocalRepositorySource(
        {"example/repo": repository_path},
    )

    repository = SimpleNamespace(
        full_name="example/repo",
    )

    with pytest.raises(
        NotADirectoryError,
        match="not a directory",
    ):
        await source.prepare(repository)  # type: ignore[arg-type]
