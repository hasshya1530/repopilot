from __future__ import annotations

import subprocess
from pathlib import Path

from agents.workspace.errors import GitCommandError


class GitService:
    """Small, controlled wrapper around the Git CLI."""

    def __init__(self, repository_path: Path) -> None:
        self._repository_path = repository_path.resolve()

        if not self._repository_path.exists():
            raise GitCommandError(
                f"Repository path does not exist: {repository_path}"
            )

        if not self._repository_path.is_dir():
            raise GitCommandError(
                f"Repository path is not a directory: {repository_path}"
            )

    def run(
        self,
        *args: str,
        check: bool = True,
    ) -> str:
        command = ("git", *args)

        completed = subprocess.run(
            command,
            cwd=self._repository_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if check and completed.returncode != 0:
            raise GitCommandError(
                "Git command failed "
                f"({completed.returncode}): "
                f"{' '.join(command)}\n"
                f"{completed.stderr.strip()}"
            )

        return completed.stdout.strip()

    def current_branch(self) -> str:
        return self.run("branch", "--show-current")

    def current_commit(self) -> str:
        return self.run("rev-parse", "HEAD")

    def is_clean(self) -> bool:
        return not bool(self.run("status", "--porcelain"))

    def status(self) -> str:
        return self.run("status", "--short")

    def diff(self) -> str:
        return self.run("diff", "--no-ext-diff")

    def create_branch(
        self,
        branch_name: str,
    ) -> None:
        self.run("switch", "-c", branch_name)

    def switch_branch(
        self,
        branch_name: str,
    ) -> None:
        self.run("switch", branch_name)

    def add(self, *paths: str) -> None:
        if not paths:
            raise GitCommandError("At least one path is required for git add.")

        self.run("add", "--", *paths)

    def commit(
        self,
        message: str,
    ) -> str:
        if not message.strip():
            raise GitCommandError("Commit message cannot be empty.")

        self.run("commit", "-m", message)
        return self.current_commit()

    def info(self) -> tuple[str, str, bool]:
        return (
            self.current_branch(),
            self.current_commit(),
            self.is_clean(),
        )
