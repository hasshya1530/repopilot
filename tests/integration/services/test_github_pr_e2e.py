from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from apps.api.app.core.config import get_settings
from apps.api.app.models.pull_request import (
    ApprovalStatus,
    PullRequestStatus,
)
from apps.api.app.models.task import Task, TaskStatus
from apps.api.app.services.github.service import GitHubService
from tools.github.client import GitHubClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_github_atomic_commit_and_pull_request_e2e(
    db_session: AsyncSession,
) -> None:
    settings = get_settings()

    if not settings.github_token:
        pytest.skip(
            "GITHUB_TOKEN is not configured; skipping real GitHub E2E test."
        )

    repository_name = settings.github_e2e_repository

    if not repository_name:
        pytest.skip(
            "GITHUB_E2E_REPOSITORY is not configured; "
            "skipping real GitHub E2E test."
        )

    if "/" not in repository_name:
        pytest.fail(
            "GITHUB_E2E_REPOSITORY must use the format owner/repository."
        )

    owner, name = repository_name.split("/", 1)

    branch_name = f"repopilot/e2e-{uuid4().hex[:10]}"

    client = GitHubClient(
        token=settings.github_token,
    )

    try:
        service = GitHubService(
            client=client,
            session=db_session,
        )

        repository = await service.sync_repository(
            owner,
            name,
        )

        task = Task(
            repository_id=repository.id,
            external_issue_id=900000000 + uuid4().int % 9000000,
            issue_number=900000000 + uuid4().int % 9000000,
            title="RepoPilot GitHub E2E",
            description=(
                "Temporary task created by the RepoPilot GitHub "
                "integration E2E test."
            ),
            status=TaskStatus.IMPLEMENTING,
        )

        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        file_path = f"repopilot_e2e_{uuid4().hex[:8]}.txt"

        implementation = ImplementationResult(
            summary="Add RepoPilot E2E marker",
            changes=(
                CodeChange(
                    file_path=file_path,
                    operation=ChangeOperation.CREATE,
                    content=(
                        "RepoPilot GitHub integration E2E passed.\n"
                    ),
                    reason=(
                        "Create a deterministic file so the atomic "
                        "commit can be verified."
                    ),
                ),
            ),
        )

        title = "test: RepoPilot GitHub integration E2E"

        body = (
            "This draft PR was created automatically by the "
            "RepoPilot GitHub integration E2E test.\n\n"
            "The test verifies branch creation, Git Data API "
            "blob/tree/commit operations, branch ref update, "
            "draft PR creation, and database persistence."
        )

        pull_request = (
            await service.create_pull_request_from_implementation(
                repository=repository,
                task=task,
                implementation=implementation,
                branch_name=branch_name,
                title=title,
                body=body,
            )
        )

        assert pull_request.id is not None
        assert pull_request.github_pr_id is not None
        assert pull_request.pr_number is not None

        assert pull_request.status == PullRequestStatus.DRAFT
        assert pull_request.approval_status == ApprovalStatus.PENDING

        assert pull_request.source_branch == branch_name
        assert pull_request.target_branch == repository.default_branch

        assert pull_request.github_url is not None

        assert task.branch_name == branch_name
        assert task.status == TaskStatus.WAITING_APPROVAL

        branch = await client.get_branch(
            owner,
            name,
            branch_name,
        )

        branch_sha = branch["commit"]["sha"]

        assert branch_sha

        github_pr = await client.get_pull_request(
            owner,
            name,
            pull_request.pr_number,
        )

        assert github_pr["number"] == pull_request.pr_number
        assert github_pr["draft"] is True
        assert github_pr["head"]["ref"] == branch_name
        assert github_pr["base"]["ref"] == repository.default_branch
        assert github_pr["state"] == "open"
        assert github_pr["html_url"] == pull_request.github_url

        # Verify the PR points to the commit created by RepoPilot.
        assert github_pr["head"]["sha"] == branch_sha

        # Verify the generated file exists in the resulting branch.
        file_data = await client.get_file(
            owner,
            name,
            file_path,
            ref=branch_name,
        )

        assert file_data["path"] == file_path
        assert file_data["type"] == "file"

    finally:
        await client._client.aclose()
