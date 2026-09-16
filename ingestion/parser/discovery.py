from dataclasses import dataclass, field
from pathlib import Path

from pathspec.gitignore import GitIgnoreSpec

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

    respect_gitignore: bool = True


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

    gitignore = _load_gitignore(repository_path, config)
    discovered: list[RepositoryFile] = []

    for path in repository_path.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(repository_path)

        if _is_ignored_directory(relative_path, config):
            continue

        relative_path_string = relative_path.as_posix()

        if gitignore is not None and gitignore.match_file(relative_path_string):
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
                relative_path=relative_path_string,
                size_bytes=size_bytes,
                extension=extension,
            )
        )

    discovered.sort(key=lambda file: file.relative_path)

    return discovered


def _load_gitignore(
    repository_path: Path,
    config: DiscoveryConfig,
) -> GitIgnoreSpec | None:
    if not config.respect_gitignore:
        return None

    gitignore_path = repository_path / ".gitignore"

    if not gitignore_path.is_file():
        return None

    try:
        content = gitignore_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    return GitIgnoreSpec.from_lines(
        content.splitlines(),
    )


def _is_ignored_directory(
    relative_path: Path,
    config: DiscoveryConfig,
) -> bool:
    return any(
        part in config.ignored_directories
        for part in relative_path.parts
    )
