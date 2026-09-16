from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
from tools.github.client import GitHubAPIError, GitHubClient


class GitHubService:
    def __init__(
        self,
        client: GitHubClient,
        session: AsyncSession,
    ) -> None:
        self.client = client
        self.session = session

    async def sync_repository(
        self,
        owner: str,
        name: str,
    ) -> Repository:
        data = await self.client.get_repository(
            owner,
            name,
        )

        github_repo_id = self._get_int(data, "id")

        result = await self.session.execute(
            select(Repository).where(Repository.github_repo_id == github_repo_id)
        )

        repository = result.scalar_one_or_none()

        values = {
            "owner": self._get_string(data, "owner", "login"),
            "name": self._get_string(data, "name"),
            "full_name": self._get_string(data, "full_name"),
            "github_repo_id": github_repo_id,
            "default_branch": self._get_string(
                data,
                "default_branch",
                default="main",
            ),
            "description": self._get_optional_string(
                data,
                "description",
            ),
            "is_private": self._get_bool(
                data,
                "private",
            ),
            "clone_url": self._get_string(
                data,
                "clone_url",
            ),
        }

        if repository is None:
            repository = Repository(**values)
            self.session.add(repository)
        else:
            for key, value in values.items():
                setattr(repository, key, value)

        await self.session.commit()
        await self.session.refresh(repository)

        return repository

    async def create_task_from_issue(
        self,
        repository: Repository,
        issue_number: int,
    ) -> Task:
        data = await self.client.get_issue(
            repository.owner,
            repository.name,
            issue_number,
        )

        existing = await self.session.execute(
            select(Task).where(
                Task.repository_id == repository.id,
                Task.issue_number == issue_number,
            )
        )

        task = existing.scalar_one_or_none()

        title = self._get_string(data, "title")
        description = self._get_optional_string(
            data,
            "body",
        )

        external_issue_id = self._get_int(
            data,
            "id",
        )

        if task is None:
            task = Task(
                repository_id=repository.id,
                external_issue_id=external_issue_id,
                issue_number=issue_number,
                title=title,
                description=description,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
        else:
            task.external_issue_id = external_issue_id
            task.title = title
            task.description = description

        await self.session.commit()
        await self.session.refresh(task)

        return task

    async def get_issue(
        self,
        repository: Repository,
        issue_number: int,
    ) -> dict[str, Any]:
        return await self.client.get_issue(
            repository.owner,
            repository.name,
            issue_number,
        )

    @staticmethod
    def _get_string(
        data: dict[str, Any],
        key: str,
        nested_key: str | None = None,
        *,
        default: str | None = None,
    ) -> str:
        value = data.get(key)

        if nested_key is not None and isinstance(value, dict):
            value = value.get(nested_key)

        if isinstance(value, str) and value:
            return value

        if default is not None:
            return default

        raise GitHubAPIError(f"GitHub response is missing required field: {key}")

    @staticmethod
    def _get_optional_string(
        data: dict[str, Any],
        key: str,
    ) -> str | None:
        value = data.get(key)

        if value is None:
            return None

        if isinstance(value, str):
            return value

        raise GitHubAPIError(f"GitHub response contains invalid field: {key}")

    @staticmethod
    def _get_int(
        data: dict[str, Any],
        key: str,
    ) -> int:
        value = data.get(key)

        if isinstance(value, int) and not isinstance(value, bool):
            return value

        raise GitHubAPIError(f"GitHub response is missing required integer field: {key}")

    @staticmethod
    def _get_bool(
        data: dict[str, Any],
        key: str,
    ) -> bool:
        value = data.get(key)

        if isinstance(value, bool):
            return value

        raise GitHubAPIError(f"GitHub response is missing required boolean field: {key}")
