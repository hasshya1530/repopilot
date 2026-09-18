from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from apps.api.app.models.pull_request import (
    ApprovalStatus,
    PullRequest,
    PullRequestStatus,
)
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
from apps.api.app.services.github.service import GitHubService


def unique_repo_values() -> dict[str, object]:
    suffix = uuid4().hex[:12]
    owner = "test-owner"
    name = f"repopilot-{suffix}"

    return {
        "owner": owner,
        "name": name,
        "full_name": f"{owner}/{name}",
        "github_repo_id": 100000000 + uuid4().int % 900000000,
        "default_branch": "main",
        "description": "RepoPilot",
        "is_private": False,
        "clone_url": f"https://github.com/{owner}/{name}.git",
    }


def unique_github_pr_id() -> int:
    return 100000000 + uuid4().int % 900000000


@pytest.mark.asyncio
async def test_sync_repository(db_session) -> None:
    repo_values = unique_repo_values()

    client = MagicMock()
    client.get_repository = AsyncMock(
        return_value={
            "id": repo_values["github_repo_id"],
            "name": repo_values["name"],
            "full_name": repo_values["full_name"],
            "owner": {
                "login": repo_values["owner"],
            },
            "default_branch": "main",
            "description": "RepoPilot",
            "private": False,
            "clone_url": repo_values["clone_url"],
        }
    )

    service = GitHubService(
        client=client,
        session=db_session,
    )

    repository = await service.sync_repository(
        repo_values["owner"],
        repo_values["name"],
    )

    assert repository.owner == repo_values["owner"]
    assert repository.name == repo_values["name"]
    assert repository.full_name == repo_values["full_name"]
    assert repository.github_repo_id == repo_values["github_repo_id"]
    assert repository.default_branch == "main"
    assert repository.is_private is False

    client.get_repository.assert_awaited_once_with(
        repo_values["owner"],
        repo_values["name"],
    )


@pytest.mark.asyncio
async def test_sync_repository_updates_existing(
    db_session,
) -> None:
    repo_values = unique_repo_values()

    existing_values = {
        **repo_values,
        "description": "old",
    }

    repository = Repository(**existing_values)

    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    client = MagicMock()

    client.get_repository = AsyncMock(
        return_value={
            "id": repo_values["github_repo_id"],
            "name": repo_values["name"],
            "full_name": repo_values["full_name"],
            "owner": {
                "login": repo_values["owner"],
            },
            "default_branch": "develop",
            "description": "updated",
            "private": True,
            "clone_url": repo_values["clone_url"],
        }
    )

    service = GitHubService(
        client=client,
        session=db_session,
    )

    updated = await service.sync_repository(
        repo_values["owner"],
        repo_values["name"],
    )

    assert updated.id == repository.id
    assert updated.owner == repo_values["owner"]
    assert updated.name == repo_values["name"]
    assert updated.full_name == repo_values["full_name"]
    assert updated.default_branch == "develop"
    assert updated.description == "updated"
    assert updated.is_private is True

    client.get_repository.assert_awaited_once_with(
        repo_values["owner"],
        repo_values["name"],
    )


@pytest.mark.asyncio
async def test_create_task_from_issue(
    db_session,
) -> None:
    repo_values = unique_repo_values()

    repository = Repository(**repo_values)

    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    client = MagicMock()

    client.get_issue = AsyncMock(
        return_value={
            "id": 999111,
            "number": 42,
            "title": "Fix authentication",
            "body": "Improve authentication handling.",
        }
    )

    service = GitHubService(
        client=client,
        session=db_session,
    )

    task = await service.create_task_from_issue(
        repository,
        42,
    )

    assert task.repository_id == repository.id
    assert task.external_issue_id == 999111
    assert task.issue_number == 42
    assert task.title == "Fix authentication"
    assert task.description == "Improve authentication handling."
    assert task.status == TaskStatus.PENDING

    client.get_issue.assert_awaited_once_with(
        repository.owner,
        repository.name,
        42,
    )


@pytest.mark.asyncio
async def test_get_issue(
    db_session,
) -> None:
    client = MagicMock()

    client.get_issue = AsyncMock(
        return_value={
            "id": 123,
            "number": 5,
            "title": "Test issue",
        }
    )

    repository = MagicMock()
    repository.owner = "test-owner"
    repository.name = "test-repo"

    service = GitHubService(
        client=client,
        session=db_session,
    )

    result = await service.get_issue(
        repository,
        5,
    )

    assert result["number"] == 5
    assert result["title"] == "Test issue"

    client.get_issue.assert_awaited_once_with(
        "test-owner",
        "test-repo",
        5,
    )


@pytest.mark.asyncio
async def test_create_pull_request_from_implementation(
    db_session,
) -> None:
    repo_values = unique_repo_values()

    repository = Repository(**repo_values)

    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    task = Task(
        repository_id=repository.id,
        external_issue_id=900001,
        issue_number=101,
        title="Add feature",
        description="Add a feature.",
        status=TaskStatus.IMPLEMENTING,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    github_pr_id = unique_github_pr_id()

    implementation = ImplementationResult(
        summary="Implement feature",
        changes=(
            CodeChange(
                file_path="src/example.py",
                operation=ChangeOperation.CREATE,
                content="print('hello')\n",
                reason="Add example module",
            ),
        ),
    )

    client = MagicMock()

    client.get_branch = AsyncMock(
        return_value={
            "name": "main",
            "commit": {
                "sha": "base-sha",
            },
        }
    )

    client.create_branch = AsyncMock(
        return_value={
            "ref": "refs/heads/repopilot/test",
        }
    )

    client.get_commit = AsyncMock(
        return_value={
            "sha": "base-sha",
            "tree": {
                "sha": "base-tree-sha",
            },
        }
    )

    client.create_blob = AsyncMock(
        return_value={
            "sha": "blob-sha",
        }
    )

    client.create_tree = AsyncMock(
        return_value={
            "sha": "tree-sha",
        }
    )

    client.create_commit = AsyncMock(
        return_value={
            "sha": "commit-sha",
        }
    )

    client.update_git_ref = AsyncMock(
        return_value={
            "ref": "refs/heads/repopilot/test",
            "object": {
                "sha": "commit-sha",
            },
        }
    )

    client.create_pull_request = AsyncMock(
        return_value={
            "id": github_pr_id,
            "number": 42,
            "html_url": (
                "https://github.com/test-owner/repopilot/pull/42"
            ),
        }
    )

    service = GitHubService(
        client=client,
        session=db_session,
    )

    pull_request = await service.create_pull_request_from_implementation(
        repository=repository,
        task=task,
        implementation=implementation,
        branch_name="repopilot/test",
        title="feat: add feature",
        body="Automated implementation.",
    )

    assert pull_request.github_pr_id == github_pr_id
    assert pull_request.pr_number == 42
    assert pull_request.status == PullRequestStatus.DRAFT
    assert pull_request.approval_status == ApprovalStatus.PENDING
    assert pull_request.source_branch == "repopilot/test"
    assert pull_request.target_branch == "main"

    assert task.branch_name == "repopilot/test"
    assert task.status == TaskStatus.WAITING_APPROVAL

    client.get_branch.assert_awaited_once_with(
        repository.owner,
        repository.name,
        "main",
    )

    client.create_branch.assert_awaited_once_with(
        repository.owner,
        repository.name,
        "repopilot/test",
        "base-sha",
    )

    client.get_commit.assert_awaited_once_with(
        repository.owner,
        repository.name,
        "base-sha",
    )

    client.create_blob.assert_awaited_once_with(
        repository.owner,
        repository.name,
        "print('hello')\n",
    )

    client.create_tree.assert_awaited_once_with(
        repository.owner,
        repository.name,
        base_tree="base-tree-sha",
        entries=[
            {
                "path": "src/example.py",
                "mode": "100644",
                "type": "blob",
                "sha": "blob-sha",
            }
        ],
    )

    client.create_commit.assert_awaited_once_with(
        repository.owner,
        repository.name,
        message="feat: Implement feature",
        tree="tree-sha",
        parents=["base-sha"],
    )

    client.update_git_ref.assert_awaited_once_with(
        repository.owner,
        repository.name,
        "heads/repopilot/test",
        "commit-sha",
    )

    client.create_pull_request.assert_awaited_once_with(
        repository.owner,
        repository.name,
        title="feat: add feature",
        body="Automated implementation.",
        head="repopilot/test",
        base="main",
        draft=True,
    )


@pytest.mark.asyncio
async def test_atomic_commit_supports_multiple_changes(
    db_session,
) -> None:
    repo_values = unique_repo_values()

    repository = Repository(**repo_values)

    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    task = Task(
        repository_id=repository.id,
        external_issue_id=900002,
        issue_number=102,
        title="Multiple changes",
        description="Multiple file changes.",
        status=TaskStatus.IMPLEMENTING,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    implementation = ImplementationResult(
        summary="Implement multiple changes",
        changes=(
            CodeChange(
                file_path="src/a.py",
                operation=ChangeOperation.CREATE,
                content="a = 1\n",
                reason="Create module A",
            ),
            CodeChange(
                file_path="src/b.py",
                operation=ChangeOperation.MODIFY,
                content="b = 2\n",
                reason="Modify module B",
            ),
        ),
    )

    client = MagicMock()

    client.get_branch = AsyncMock(
        return_value={
            "commit": {
                "sha": "base-sha",
            },
        }
    )

    client.create_branch = AsyncMock()

    client.get_commit = AsyncMock(
        return_value={
            "tree": {
                "sha": "base-tree",
            },
        }
    )

    client.create_blob = AsyncMock(
        side_effect=[
            {"sha": "blob-a"},
            {"sha": "blob-b"},
        ]
    )

    client.create_tree = AsyncMock(
        return_value={
            "sha": "new-tree",
        }
    )

    client.create_commit = AsyncMock(
        return_value={
            "sha": "new-commit",
        }
    )

    client.update_git_ref = AsyncMock()

    client.create_pull_request = AsyncMock(
        return_value={
            "id": unique_github_pr_id(),
            "number": 43,
            "html_url": "https://github.com/test-owner/repopilot/pull/43",
        }
    )

    service = GitHubService(
        client=client,
        session=db_session,
    )

    await service.create_pull_request_from_implementation(
        repository=repository,
        task=task,
        implementation=implementation,
        branch_name="repopilot/multiple",
        title="feat: multiple changes",
        body="Multiple changes.",
    )

    assert client.create_blob.await_count == 2
    client.create_tree.assert_awaited_once()
    client.create_commit.assert_awaited_once()
    client.update_git_ref.assert_awaited_once()
    client.create_pull_request.assert_awaited_once()

    tree_call = client.create_tree.await_args

    assert tree_call is not None
    assert tree_call.kwargs["base_tree"] == "base-tree"
    assert tree_call.kwargs["entries"] == [
        {
            "path": "src/a.py",
            "mode": "100644",
            "type": "blob",
            "sha": "blob-a",
        },
        {
            "path": "src/b.py",
            "mode": "100644",
            "type": "blob",
            "sha": "blob-b",
        },
    ]


@pytest.mark.asyncio
async def test_atomic_commit_supports_delete(
    db_session,
) -> None:
    repo_values = unique_repo_values()

    repository = Repository(**repo_values)

    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    task = Task(
        repository_id=repository.id,
        external_issue_id=900003,
        issue_number=103,
        title="Delete old file",
        description="Delete an obsolete file.",
        status=TaskStatus.IMPLEMENTING,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    implementation = ImplementationResult(
        summary="Remove obsolete file",
        changes=(
            CodeChange(
                file_path="src/old.py",
                operation=ChangeOperation.DELETE,
                content="",
                reason="Remove obsolete module",
            ),
        ),
    )

    client = MagicMock()

    client.get_branch = AsyncMock(
        return_value={
            "commit": {
                "sha": "base-sha",
            },
        }
    )

    client.create_branch = AsyncMock()

    client.get_commit = AsyncMock(
        return_value={
            "tree": {
                "sha": "base-tree",
            },
        }
    )

    client.create_blob = AsyncMock()

    client.create_tree = AsyncMock(
        return_value={
            "sha": "new-tree",
        }
    )

    client.create_commit = AsyncMock(
        return_value={
            "sha": "new-commit",
        }
    )

    client.update_git_ref = AsyncMock()

    client.create_pull_request = AsyncMock(
        return_value={
            "id": unique_github_pr_id(),
            "number": 44,
            "html_url": "https://github.com/test-owner/repopilot/pull/44",
        }
    )

    service = GitHubService(
        client=client,
        session=db_session,
    )

    await service.create_pull_request_from_implementation(
        repository=repository,
        task=task,
        implementation=implementation,
        branch_name="repopilot/delete",
        title="feat: remove obsolete file",
        body="Remove obsolete file.",
    )

    client.create_blob.assert_not_awaited()

    client.create_tree.assert_awaited_once_with(
        repository.owner,
        repository.name,
        base_tree="base-tree",
        entries=[
            {
                "path": "src/old.py",
                "mode": "100644",
                "type": "blob",
                "sha": None,
            }
        ],
    )

    client.create_commit.assert_awaited_once_with(
        repository.owner,
        repository.name,
        message="feat: Remove obsolete file",
        tree="new-tree",
        parents=["base-sha"],
    )


@pytest.mark.asyncio
async def test_create_pull_request_rejects_empty_implementation(
    db_session,
) -> None:
    repo_values = unique_repo_values()

    repository = Repository(**repo_values)

    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    task = Task(
        repository_id=repository.id,
        external_issue_id=900004,
        issue_number=104,
        title="Empty implementation",
        description="No changes.",
        status=TaskStatus.IMPLEMENTING,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    implementation = ImplementationResult(
        summary="No changes",
        changes=(),
    )

    client = MagicMock()

    service = GitHubService(
        client=client,
        session=db_session,
    )

    with pytest.raises(
        ValueError,
        match="without implementation changes",
    ):
        await service.create_pull_request_from_implementation(
            repository=repository,
            task=task,
            implementation=implementation,
            branch_name="repopilot/empty",
            title="feat: empty",
            body="Empty.",
        )

    client.get_branch.assert_not_called()


@pytest.mark.asyncio
async def test_create_pull_request_rejects_duplicate_branch(
    db_session,
) -> None:
    repo_values = unique_repo_values()

    repository = Repository(**repo_values)

    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    task = Task(
        repository_id=repository.id,
        external_issue_id=900005,
        issue_number=105,
        title="Duplicate",
        description="Duplicate branch.",
        status=TaskStatus.IMPLEMENTING,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    existing = PullRequest(
        task_id=task.id,
        github_pr_id=unique_github_pr_id(),
        pr_number=50,
        title="Existing",
        description="Existing PR.",
        source_branch="repopilot/duplicate",
        target_branch="main",
        status=PullRequestStatus.DRAFT,
        approval_status=ApprovalStatus.PENDING,
    )

    db_session.add(existing)
    await db_session.commit()

    implementation = ImplementationResult(
        summary="Duplicate",
        changes=(
            CodeChange(
                file_path="example.py",
                operation=ChangeOperation.CREATE,
                content="x = 1\n",
                reason="Test",
            ),
        ),
    )

    client = MagicMock()

    service = GitHubService(
        client=client,
        session=db_session,
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        await service.create_pull_request_from_implementation(
            repository=repository,
            task=task,
            implementation=implementation,
            branch_name="repopilot/duplicate",
            title="feat: duplicate",
            body="Duplicate.",
        )

    client.get_branch.assert_not_called()


@pytest.mark.asyncio
async def test_create_pull_request_rejects_task_from_other_repository(
    db_session,
) -> None:
    repo_values = unique_repo_values()
    other_repo_values = unique_repo_values()

    repository = Repository(**repo_values)
    other_repository = Repository(**other_repo_values)

    db_session.add_all(
        [
            repository,
            other_repository,
        ]
    )

    await db_session.commit()
    await db_session.refresh(repository)
    await db_session.refresh(other_repository)

    task = Task(
        repository_id=other_repository.id,
        external_issue_id=900006,
        issue_number=106,
        title="Wrong repository",
        description="Wrong repository.",
        status=TaskStatus.IMPLEMENTING,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    implementation = ImplementationResult(
        summary="Wrong repository",
        changes=(
            CodeChange(
                file_path="example.py",
                operation=ChangeOperation.CREATE,
                content="x = 1\n",
                reason="Test",
            ),
        ),
    )

    client = MagicMock()

    service = GitHubService(
        client=client,
        session=db_session,
    )

    with pytest.raises(
        ValueError,
        match="does not belong",
    ):
        await service.create_pull_request_from_implementation(
            repository=repository,
            task=task,
            implementation=implementation,
            branch_name="repopilot/wrong-repo",
            title="feat: wrong repo",
            body="Wrong repository.",
        )

    client.get_branch.assert_not_called()
