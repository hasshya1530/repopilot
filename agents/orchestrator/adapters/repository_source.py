from pathlib import Path

from apps.api.app.models.repository import Repository


class LocalRepositorySource:
    """Resolves persisted repositories to already-existing local checkouts."""

    def __init__(
        self,
        repositories: dict[str, Path],
    ) -> None:
        self._repositories = {
            full_name: path.resolve()
            for full_name, path in repositories.items()
        }

    async def prepare(
        self,
        repository: Repository,
    ) -> Path:
        path = self._repositories.get(repository.full_name)

        if path is None:
            raise FileNotFoundError(
                f"No local checkout configured for repository "
                f"{repository.full_name!r}."
            )

        if not path.exists():
            raise FileNotFoundError(
                f"Local repository checkout does not exist: {path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Local repository checkout is not a directory: {path}"
            )

        return path
