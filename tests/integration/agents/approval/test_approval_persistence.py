from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agents.approval.models import ApprovalDecision, ApprovalRequest
from agents.approval.repository import SQLAlchemyApprovalRepository
from agents.approval.service import ApprovalService
from apps.api.app.models.pull_request import (
    ApprovalStatus,
    PullRequest,
    PullRequestStatus,
)
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus


@pytest.mark.integration
@pytest.mark.asyncio
async def test_approval_lifecycle_persists_to_postgresql(
    db_session: AsyncSession,
) -> None:
    suffix = uuid4().hex[:12]

    repository = Repository(
        owner="approval-integration",
        name=f"approval-{suffix}",
        full_name=f"approval-integration/approval-{suffix}",
        github_repo_id=uuid4().int % 2_000_000_000,
        default_branch="main",
        description="Approval integration test repository",
        is_private=False,
        clone_url=(
            f"https://github.com/approval-integration/approval-{suffix}.git"
        ),
    )

    db_session.add(repository)
    await db_session.flush()

    task = Task(
        repository_id=repository.id,
        title=f"Approval integration task {suffix}",
        description="Test human approval persistence.",
        status=TaskStatus.WAITING_APPROVAL,
        branch_name=f"repopilot/approval-{suffix}",
    )

    db_session.add(task)
    await db_session.flush()

    pull_request = PullRequest(
        task_id=task.id,
        title="Approval integration test",
        description="Test approval persistence.",
        source_branch=task.branch_name,
        target_branch="main",
        status=PullRequestStatus.DRAFT,
        approval_status=ApprovalStatus.PENDING,
    )

    db_session.add(pull_request)
    await db_session.commit()

    pull_request_id = pull_request.id

    repository_service = SQLAlchemyApprovalRepository(db_session)
    service = ApprovalService(repository_service)

    initial = await service.get_status(
        ApprovalRequest(pull_request_id=pull_request_id)
    )

    assert initial.status == ApprovalStatus.PENDING
    assert initial.pending is True

    decision = await service.decide(
        ApprovalDecision(
            pull_request_id=pull_request_id,
            status=ApprovalStatus.APPROVED,
            reason="Human reviewer approved the proposed changes.",
        )
    )

    assert decision.status == ApprovalStatus.APPROVED
    assert decision.approved is True

    db_session.expire_all()

    persisted = await db_session.get(PullRequest, pull_request_id)

    assert persisted is not None
    assert persisted.approval_status == ApprovalStatus.APPROVED

    verified = await service.require_approval(pull_request_id)

    assert verified.approved is True
    assert verified.status == ApprovalStatus.APPROVED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rejected_approval_is_persisted(
    db_session: AsyncSession,
) -> None:
    suffix = uuid4().hex[:12]

    repository = Repository(
        owner="approval-integration",
        name=f"rejection-{suffix}",
        full_name=f"approval-integration/rejection-{suffix}",
        github_repo_id=uuid4().int % 2_000_000_000,
        default_branch="main",
        description="Approval rejection integration test repository",
        is_private=False,
        clone_url=(
            f"https://github.com/approval-integration/rejection-{suffix}.git"
        ),
    )

    db_session.add(repository)
    await db_session.flush()

    task = Task(
        repository_id=repository.id,
        title=f"Approval rejection task {suffix}",
        status=TaskStatus.WAITING_APPROVAL,
        branch_name=f"repopilot/rejection-{suffix}",
    )

    db_session.add(task)
    await db_session.flush()

    pull_request = PullRequest(
        task_id=task.id,
        title="Approval rejection integration test",
        source_branch=task.branch_name,
        target_branch="main",
        status=PullRequestStatus.DRAFT,
        approval_status=ApprovalStatus.PENDING,
    )

    db_session.add(pull_request)
    await db_session.commit()

    pull_request_id = pull_request.id

    service = ApprovalService(
        SQLAlchemyApprovalRepository(db_session)
    )

    result = await service.decide(
        ApprovalDecision(
            pull_request_id=pull_request_id,
            status=ApprovalStatus.REJECTED,
            reason="Changes require another review.",
        )
    )

    assert result.rejected is True

    db_session.expire_all()

    persisted = await db_session.get(PullRequest, pull_request_id)

    assert persisted is not None
    assert persisted.approval_status == ApprovalStatus.REJECTED
