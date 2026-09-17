from pathlib import Path

import pytest

from agents.workspace.errors import (
    WorkspaceConfigurationError,
    WorkspaceStateError,
)
from agents.workspace.git_service import GitService
from agents.workspace.service import WorkspaceManager


def initialize_repository(path: Path) -> None:
    git = GitService(path)

    git.run("init")
    git.run("config", "user.email", "test@repopilot.local")
    git.run("config", "user.name", "RepoPilot Test")
    git.run("add", "--all")
    git.run("commit", "-m", "initial commit")


def test_create_isolated_workspace(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "auth.py").write_text(
        "def validate_token(token):\n"
        "    return bool(token)\n"
    )

    initialize_repository(source)

    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create_from_repository(
        source,
        branch_name="repopilot/test-change",
    )

    assert workspace.exists()
    assert workspace != source

    workspace_git = GitService(workspace)

    assert workspace_git.current_branch() == "repopilot/test-change"
    assert workspace_git.is_clean()

    assert (workspace / "auth.py").read_text() == (
        "def validate_token(token):\n"
        "    return bool(token)\n"
    )


def test_workspace_changes_do_not_modify_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    original = "return False\n"
    (source / "auth.py").write_text(original)

    initialize_repository(source)

    manager = WorkspaceManager(tmp_path / "workspaces")
    workspace = manager.create_from_repository(source)

    (workspace / "auth.py").write_text("return True\n")

    assert (source / "auth.py").read_text() == original
    assert (workspace / "auth.py").read_text() == "return True\n"


def test_workspace_info(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "README.md").write_text("# RepoPilot\n")
    initialize_repository(source)

    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create_from_repository(
        source,
        branch_name="repopilot/info-test",
    )

    info = manager.info(workspace)

    assert info.path == str(workspace.resolve())
    assert info.branch_name == "repopilot/info-test"
    assert len(info.commit_sha) == 40
    assert info.is_clean is True


def test_remove_workspace(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "README.md").write_text("# RepoPilot\n")
    initialize_repository(source)

    root = tmp_path / "workspaces"
    manager = WorkspaceManager(root)

    workspace = manager.create_from_repository(source)

    assert workspace.exists()

    manager.remove(workspace)

    assert not workspace.exists()
    assert root.exists()


def test_rejects_dirty_source_repository(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "README.md").write_text("# initial\n")
    initialize_repository(source)

    (source / "README.md").write_text("# modified\n")

    manager = WorkspaceManager(tmp_path / "workspaces")

    with pytest.raises(WorkspaceStateError):
        manager.create_from_repository(source)


def test_rejects_workspace_removal_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    manager = WorkspaceManager(root)

    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(WorkspaceConfigurationError):
        manager.remove(outside)
