from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.implementer.models import ChangeOperation, ImplementationResult
from apps.api.app.models.pull_request import (
    ApprovalStatus,
    PullRequest,
    PullRequestStatus,
)
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
            select(Repository).where(
                Repository.github_repo_id == github_repo_id
            )
        )

        repository = result.scalar_one_or_none()

        values = {
            "owner": self._get_string(
                data,
                "owner",
                "login",
            ),
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

        result = await self.session.execute(
            select(Task).where(
                Task.repository_id == repository.id,
                Task.issue_number == issue_number,
            )
        )

        task = result.scalar_one_or_none()

        external_issue_id = self._get_int(data, "id")
        title = self._get_string(data, "title")
        description = self._get_optional_string(data, "body")

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

    async def _create_atomic_commit(
        self,
        *,
        repository: Repository,
        implementation: ImplementationResult,
        base_sha: str,
        branch_name: str,
    ) -> str:
        commit = await self.client.get_commit(
            repository.owner,
            repository.name,
            base_sha,
        )

        base_tree = self._get_string(
            commit,
            "tree",
            "sha",
        )

        tree_entries: list[dict[str, Any]] = []

        for change in implementation.changes:
            if change.operation == ChangeOperation.DELETE:
                tree_entries.append(
                    {
                        "path": change.file_path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": None,
                    }
                )
                continue

            blob = await self.client.create_blob(
                repository.owner,
                repository.name,
                change.content,
            )

            blob_sha = self._get_string(
                blob,
                "sha",
            )

            tree_entries.append(
                {
                    "path": change.file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha,
                }
            )

        tree = await self.client.create_tree(
            repository.owner,
            repository.name,
            base_tree=base_tree,
            entries=tree_entries,
        )

        tree_sha = self._get_string(
            tree,
            "sha",
        )

        commit_result = await self.client.create_commit(
            repository.owner,
            repository.name,
            message=f"feat: {implementation.summary}",
            tree=tree_sha,
            parents=[base_sha],
        )

        commit_sha = self._get_string(
            commit_result,
            "sha",
        )

        await self.client.update_git_ref(
            repository.owner,
            repository.name,
            f"heads/{branch_name}",
            commit_sha,
        )

        return commit_sha

    async def create_pull_request_from_implementation(
        self,
        *,
        repository: Repository,
        task: Task,
        implementation: ImplementationResult,
        branch_name: str,
        title: str,
        body: str,
    ) -> PullRequest:
        if not branch_name.strip():
            raise ValueError("Branch name must not be empty.")

        if not implementation.changes:
            raise ValueError(
                "Cannot create a pull request without implementation changes."
            )

        if task.repository_id != repository.id:
            raise ValueError(
                "Task does not belong to the supplied repository."
            )

        existing_result = await self.session.execute(
            select(PullRequest).where(
                PullRequest.task_id == task.id,
                PullRequest.source_branch == branch_name,
            )
        )

        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            raise ValueError(
                f"A pull request already exists for branch '{branch_name}'."
            )

        base_branch = repository.default_branch

        base = await self.client.get_branch(
            repository.owner,
            repository.name,
            base_branch,
        )

        base_sha = self._get_string(
            base,
            "commit",
            "sha",
        )

        await self.client.create_branch(
            repository.owner,
            repository.name,
            branch_name,
            base_sha,
        )

        await self._create_atomic_commit(
            repository=repository,
            implementation=implementation,
            base_sha=base_sha,
            branch_name=branch_name,
        )

        github_pr = await self.client.create_pull_request(
            repository.owner,
            repository.name,
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
            draft=True,
        )

        pr_number = self._get_int(
            github_pr,
            "number",
        )

        github_url = self._get_optional_string(
            github_pr,
            "html_url",
        )

        pull_request = PullRequest(
            task_id=task.id,
            github_pr_id=self._get_optional_int(
                github_pr,
                "id",
            ),
            pr_number=pr_number,
            title=title,
            description=body,
            source_branch=branch_name,
            target_branch=base_branch,
            status=PullRequestStatus.DRAFT,
            approval_status=ApprovalStatus.PENDING,
            github_url=github_url,
        )

        self.session.add(pull_request)

        task.branch_name = branch_name
        task.status = TaskStatus.WAITING_APPROVAL

        await self.session.commit()
        await self.session.refresh(pull_request)

        return pull_request

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

        raise GitHubAPIError(
            f"GitHub response is missing required field: {key}"
        )

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

        raise GitHubAPIError(
            f"GitHub response contains invalid field: {key}"
        )

    @staticmethod
    def _get_int(
        data: dict[str, Any],
        key: str,
    ) -> int:
        value = data.get(key)

        if isinstance(value, int) and not isinstance(value, bool):
            return value

        raise GitHubAPIError(
            f"GitHub response is missing required integer field: {key}"
        )

    @staticmethod
    def _get_optional_int(
        data: dict[str, Any],
        key: str,
    ) -> int | None:
        value = data.get(key)

        if value is None:
            return None

        if isinstance(value, int) and not isinstance(value, bool):
            return value

        raise GitHubAPIError(
            f"GitHub response contains invalid integer field: {key}"
        )

    @staticmethod
    def _get_bool(
        data: dict[str, Any],
        key: str,
    ) -> bool:
        value = data.get(key)

        if isinstance(value, bool):
            return value

        raise GitHubAPIError(
            f"GitHub response is missing required boolean field: {key}"
        )
