from pathlib import Path

import pytest

from agents.workspace.errors import WorkspaceConfigurationError
from agents.workspace.git_service import GitService
from agents.workspace.service import WorkspaceManager


def initialize_repository(path: Path) -> None:
    git = GitService(path)
    git.run("init")
    git.run("config", "user.email", "test@example.com")
    git.run("config", "user.name", "RepoPilot Test")
    git.run("add", "--all")
    git.run("commit", "-m", "initial")


def test_creates_workspace_from_clean_repository(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "README.md").write_text("# initial\n")
    initialize_repository(source)

    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create_from_repository(source)

    assert workspace.exists()
    assert (workspace / "README.md").read_text() == "# initial\n"

    info = manager.info(workspace)

    assert info.is_clean is True
    assert info.branch_name.startswith("repopilot/")


def test_creates_workspace_from_dirty_repository(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "README.md").write_text("# initial\n")
    initialize_repository(source)

    (source / "README.md").write_text("# modified\n")

    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create_from_repository(source)

    assert workspace.exists()
    assert (workspace / "README.md").read_text() == "# modified\n"

    info = manager.info(workspace)

    assert info.is_clean is True
    assert info.branch_name.startswith("repopilot/")


def test_workspace_creates_fresh_git_repository(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "README.md").write_text("# initial\n")
    initialize_repository(source)

    source_git = GitService(source)
    source_commit = source_git.info()[1]

    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create_from_repository(source)

    assert (workspace / ".git").is_dir()

    workspace_git = GitService(workspace)
    workspace_commit = workspace_git.info()[1]

    assert workspace_commit != source_commit


def test_workspace_does_not_copy_source_git_history(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "README.md").write_text("# initial\n")
    initialize_repository(source)

    source_git = GitService(source)
    source_commit = source_git.info()[1]

    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create_from_repository(source)

    workspace_git = GitService(workspace)
    log = workspace_git.run("log", "--oneline")

    assert source_commit not in log


def test_rejects_missing_source_repository(tmp_path: Path) -> None:
    source = tmp_path / "missing"

    manager = WorkspaceManager(tmp_path / "workspaces")

    with pytest.raises(WorkspaceConfigurationError):
        manager.create_from_repository(source)


def test_rejects_source_file(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("not a repository")

    manager = WorkspaceManager(tmp_path / "workspaces")

    with pytest.raises(WorkspaceConfigurationError):
        manager.create_from_repository(source)


def test_cannot_remove_workspace_root(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    manager = WorkspaceManager(workspace_root)

    with pytest.raises(WorkspaceConfigurationError):
        manager.remove(workspace_root)


def test_cannot_remove_workspace_outside_managed_root(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspaces"
    outside = tmp_path / "outside"
    outside.mkdir()

    manager = WorkspaceManager(workspace_root)

    with pytest.raises(WorkspaceConfigurationError):
        manager.remove(outside)
