from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.task import TaskStatus
from apps.api.app.schemas.repository import RepositoryCreate
from apps.api.app.services.github import GitHubService
from apps.api.app.services.repository import create_repository
from tools.github.client import GitHubClient


@pytest.mark.asyncio
async def test_sync_repository_creates_repository(
    db_session: AsyncSession,
) -> None:
    client = AsyncMock(spec=GitHubClient)

    client.get_repository.return_value = {
        "id": 987654,
        "name": "repopilot",
        "full_name": "hasshya1530/repopilot",
        "owner": {
            "login": "hasshya1530",
        },
        "default_branch": "main",
        "description": "Autonomous software engineering agent.",
        "private": False,
        "clone_url": "https://github.com/hasshya1530/repopilot.git",
    }

    service = GitHubService(
        client=client,
        session=db_session,
    )

    repository = await service.sync_repository(
        "hasshya1530",
        "repopilot",
    )

    assert repository.github_repo_id == 987654
    assert repository.owner == "hasshya1530"
    assert repository.name == "repopilot"
    assert repository.full_name == "hasshya1530/repopilot"
    assert repository.default_branch == "main"
    assert repository.is_private is False

    client.get_repository.assert_awaited_once_with(
        "hasshya1530",
        "repopilot",
    )


@pytest.mark.asyncio
async def test_sync_repository_updates_existing_repository(
    db_session: AsyncSession,
) -> None:
    repository = await create_repository(
        db_session,
        RepositoryCreate(
            owner="hasshya1530",
            name="repopilot",
            full_name="hasshya1530/repopilot",
            github_repo_id=987655,
            default_branch="main",
            description="Old description",
            is_private=False,
            clone_url="https://github.com/hasshya1530/repopilot.git",
        ),
    )

    client = AsyncMock(spec=GitHubClient)

    client.get_repository.return_value = {
        "id": 987655,
        "name": "repopilot",
        "full_name": "hasshya1530/repopilot",
        "owner": {
            "login": "hasshya1530",
        },
        "default_branch": "develop",
        "description": "Updated description",
        "private": True,
        "clone_url": "https://github.com/hasshya1530/repopilot.git",
    }

    service = GitHubService(
        client=client,
        session=db_session,
    )

    updated = await service.sync_repository(
        "hasshya1530",
        "repopilot",
    )

    assert updated.id == repository.id
    assert updated.default_branch == "develop"
    assert updated.description == "Updated description"
    assert updated.is_private is True


@pytest.mark.asyncio
async def test_create_task_from_issue(
    db_session: AsyncSession,
) -> None:
    repository = await create_repository(
        db_session,
        RepositoryCreate(
            owner="hasshya1530",
            name="repopilot",
            full_name="hasshya1530/repopilot",
            github_repo_id=987656,
            default_branch="main",
            description=None,
            is_private=False,
            clone_url="https://github.com/hasshya1530/repopilot.git",
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
        "repopilot",
        42,
    )


@pytest.mark.asyncio
async def test_create_task_from_issue_updates_existing_task(
    db_session: AsyncSession,
) -> None:
    repository = await create_repository(
        db_session,
        RepositoryCreate(
            owner="hasshya1530",
            name="repopilot",
            full_name="hasshya1530/repopilot",
            github_repo_id=987657,
            default_branch="main",
            description=None,
            is_private=False,
            clone_url="https://github.com/hasshya1530/repopilot.git",
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
