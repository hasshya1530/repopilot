from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from agents.workspace.errors import (
    WorkspaceConfigurationError,
    WorkspaceStateError,
)
from agents.workspace.git_service import GitService
from agents.workspace.models import WorkspaceInfo


class WorkspaceManager:
    """Creates and manages isolated local Git workspaces."""

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path.resolve()

        if self._root_path.exists() and not self._root_path.is_dir():
            raise WorkspaceConfigurationError(
                f"Workspace root is not a directory: {root_path}"
            )

        self._root_path.mkdir(parents=True, exist_ok=True)

    def create_from_repository(
        self,
        repository_path: Path,
        *,
        branch_name: str | None = None,
    ) -> Path:
        source = repository_path.resolve()

        if not source.exists():
            raise WorkspaceConfigurationError(
                f"Source repository does not exist: {repository_path}"
            )

        git = GitService(source)

        if not git.is_clean():
            raise WorkspaceStateError(
                "Source repository must be clean before creating a workspace."
            )

        workspace_name = uuid.uuid4().hex
        workspace_path = self._root_path / workspace_name

        try:
            shutil.copytree(
                source,
                workspace_path,
                ignore=shutil.ignore_patterns(".git"),
            )

            workspace_git = GitService(workspace_path)

            workspace_git.run("init")
            workspace_git.run("remote", "add", "origin", str(source))
            workspace_git.run("add", "--all")
            workspace_git.run(
                "commit",
                "-m",
                "chore: initialize RepoPilot workspace",
            )

            branch = branch_name or f"repopilot/{uuid.uuid4().hex[:12]}"

            workspace_git.create_branch(branch)

            return workspace_path

        except Exception:
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            raise

    def info(
        self,
        workspace_path: Path,
    ) -> WorkspaceInfo:
        git = GitService(workspace_path)
        branch, commit, clean = git.info()

        return WorkspaceInfo(
            path=str(workspace_path.resolve()),
            branch_name=branch,
            commit_sha=commit,
            is_clean=clean,
        )

    def remove(
        self,
        workspace_path: Path,
    ) -> None:
        workspace = workspace_path.resolve()

        try:
            workspace.relative_to(self._root_path)
        except ValueError as exc:
            raise WorkspaceConfigurationError(
                f"Workspace is outside managed root: {workspace_path}"
            ) from exc

        if workspace == self._root_path:
            raise WorkspaceConfigurationError(
                "Cannot remove the workspace root."
            )

        if workspace.exists():
            shutil.rmtree(workspace)
