from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.task import TaskStatus
from apps.api.app.schemas.repository import RepositoryCreate
from apps.api.app.services.github import GitHubService
from apps.api.app.services.repository import create_repository
from tools.github.client import GitHubClient


def unique_repository_name(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_sync_repository_creates_repository(
    db_session: AsyncSession,
) -> None:
    name = unique_repository_name("repopilot-sync-create")
    full_name = f"hasshya1530/{name}"

    client = AsyncMock(spec=GitHubClient)

    client.get_repository.return_value = {
        "id": 1000000 + uuid4().int % 900000,
        "name": name,
        "full_name": full_name,
        "owner": {
            "login": "hasshya1530",
        },
        "default_branch": "main",
        "description": "Autonomous software engineering agent.",
        "private": False,
        "clone_url": f"https://github.com/{full_name}.git",
    }

    service = GitHubService(
        client=client,
        session=db_session,
    )

    repository = await service.sync_repository(
        "hasshya1530",
        name,
    )

    assert repository.github_repo_id == client.get_repository.return_value["id"]
    assert repository.owner == "hasshya1530"
    assert repository.name == name
    assert repository.full_name == full_name
    assert repository.default_branch == "main"
    assert repository.is_private is False

    client.get_repository.assert_awaited_once_with(
        "hasshya1530",
        name,
    )


@pytest.mark.asyncio
async def test_sync_repository_updates_existing_repository(
    db_session: AsyncSession,
) -> None:
    name = unique_repository_name("repopilot-sync-update")
    full_name = f"hasshya1530/{name}"
    github_repo_id = 2000000 + uuid4().int % 900000

    repository = await create_repository(
        db_session,
        RepositoryCreate(
            owner="hasshya1530",
            name=name,
            full_name=full_name,
            github_repo_id=github_repo_id,
            default_branch="main",
            description="Old description",
            is_private=False,
            clone_url=f"https://github.com/{full_name}.git",
        ),
    )

    client = AsyncMock(spec=GitHubClient)

    client.get_repository.return_value = {
        "id": github_repo_id,
        "name": name,
        "full_name": full_name,
        "owner": {
            "login": "hasshya1530",
        },
        "default_branch": "develop",
        "description": "Updated description",
        "private": True,
        "clone_url": f"https://github.com/{full_name}.git",
    }

    service = GitHubService(
        client=client,
        session=db_session,
    )

    updated = await service.sync_repository(
        "hasshya1530",
        name,
    )

    assert updated.id == repository.id
    assert updated.default_branch == "develop"
    assert updated.description == "Updated description"
    assert updated.is_private is True

    client.get_repository.assert_awaited_once_with(
        "hasshya1530",
        name,
    )


@pytest.mark.asyncio
async def test_create_task_from_issue(
    db_session: AsyncSession,
) -> None:
    name = unique_repository_name("repopilot-issue-create")
    full_name = f"hasshya1530/{name}"
    github_repo_id = 3000000 + uuid4().int % 900000

    repository = await create_repository(
        db_session,
        RepositoryCreate(
            owner="hasshya1530",
            name=name,
            full_name=full_name,
            github_repo_id=github_repo_id,
            default_branch="main",
            description=None,
            is_private=False,
            clone_url=f"https://github.com/{full_name}.git",
        ),
    )

    client = AsyncMock(spec=GitHubClient)

    client.get_issue.return_value = {
        "id": 555555,
        "number": 42,
        "title": "Add repository indexing",
        "body": "Implement repository indexing.",
    }

    service = GitHubService(
        client=client,
        session=db_session,
    )

    task = await service.create_task_from_issue(
        repository,
        42,
    )

    assert task.repository_id == repository.id
    assert task.external_issue_id == 555555
    assert task.issue_number == 42
    assert task.title == "Add repository indexing"
    assert task.description == "Implement repository indexing."
    assert task.status == TaskStatus.PENDING

    client.get_issue.assert_awaited_once_with(
        "hasshya1530",
        name,
        42,
    )


@pytest.mark.asyncio
async def test_create_task_from_issue_updates_existing_task(
    db_session: AsyncSession,
) -> None:
    name = unique_repository_name("repopilot-issue-update")
    full_name = f"hasshya1530/{name}"
    github_repo_id = 4000000 + uuid4().int % 900000

    repository = await create_repository(
        db_session,
        RepositoryCreate(
            owner="hasshya1530",
            name=name,
            full_name=full_name,
            github_repo_id=github_repo_id,
            default_branch="main",
            description=None,
            is_private=False,
            clone_url=f"https://github.com/{full_name}.git",
        ),
    )

    client = AsyncMock(spec=GitHubClient)

    client.get_issue.return_value = {
        "id": 555556,
        "number": 7,
        "title": "Updated issue title",
        "body": "Updated issue description.",
    }

    service = GitHubService(
        client=client,
        session=db_session,
    )

    first_task = await service.create_task_from_issue(
        repository,
        7,
    )

    updated_task = await service.create_task_from_issue(
        repository,
        7,
    )

    assert updated_task.id == first_task.id
    assert updated_task.title == "Updated issue title"
    assert updated_task.description == "Updated issue description."

    client.get_issue.assert_awaited_with(
        "hasshya1530",
        name,
        7,
    )
