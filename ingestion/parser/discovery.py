from dataclasses import dataclass, field
from pathlib import Path

from ingestion.parser.files import RepositoryFile


@dataclass(frozen=True, slots=True)
class DiscoveryConfig:
    max_file_size_bytes: int = 1_000_000

    ignored_directories: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "dist",
                "build",
                "coverage",
                ".next",
            }
        )
    )

    ignored_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                ".pyc",
                ".pyo",
                ".so",
                ".dll",
                ".dylib",
                ".class",
                ".o",
                ".a",
                ".bin",
                ".exe",
            }
        )
    )


def discover_files(
    repository_path: Path,
    config: DiscoveryConfig | None = None,
) -> list[RepositoryFile]:
    if config is None:
        config = DiscoveryConfig()

    if not repository_path.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {repository_path}"
        )

    if not repository_path.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {repository_path}"
        )

    discovered: list[RepositoryFile] = []

    for path in repository_path.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(repository_path)

        if _is_ignored_directory(relative_path, config):
            continue

        extension = path.suffix.lower()

        if extension in config.ignored_extensions:
            continue

        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue

        if size_bytes > config.max_file_size_bytes:
            continue

        discovered.append(
            RepositoryFile(
                path=path,
                relative_path=relative_path.as_posix(),
                size_bytes=size_bytes,
                extension=extension,
            )
        )

    discovered.sort(key=lambda file: file.relative_path)

    return discovered


def _is_ignored_directory(
    relative_path: Path,
    config: DiscoveryConfig,
) -> bool:
    return any(
        part in config.ignored_directories
        for part in relative_path.parts
    )
