from uuid import UUID

import pytest

from agents.approval.errors import (
    ApprovalNotFoundError,
    ApprovalRequiredError,
    InvalidApprovalTransitionError,
)
from agents.approval.models import ApprovalDecision, ApprovalRequest
from agents.approval.service import ApprovalService
from apps.api.app.models.pull_request import ApprovalStatus

PULL_REQUEST_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakeApprovalRepository:
    def __init__(
        self,
        status: ApprovalStatus | None = ApprovalStatus.PENDING,
    ) -> None:
        self.status = status
        self.saved: tuple[
            UUID,
            ApprovalStatus,
            str | None,
        ] | None = None

    async def get_approval_status(
        self,
        pull_request_id: UUID,
    ) -> ApprovalStatus | None:
        return self.status

    async def set_approval_status(
        self,
        pull_request_id: UUID,
        status: ApprovalStatus,
        reason: str | None,
        expected_status: ApprovalStatus,
    ) -> bool:
        if self.status != expected_status:
            return False

        self.saved = (pull_request_id, status, reason)
        self.status = status
        return True


@pytest.mark.asyncio
async def test_get_status_returns_pending() -> None:
    repository = FakeApprovalRepository()
    service = ApprovalService(repository)

    result = await service.get_status(
        ApprovalRequest(pull_request_id=PULL_REQUEST_ID)
    )

    assert result.status == ApprovalStatus.PENDING
    assert result.pending is True
    assert result.approved is False


@pytest.mark.asyncio
async def test_approve_pending_request() -> None:
    repository = FakeApprovalRepository()
    service = ApprovalService(repository)

    result = await service.decide(
        ApprovalDecision(
            pull_request_id=PULL_REQUEST_ID,
            status=ApprovalStatus.APPROVED,
            reason="Reviewed and approved.",
        )
    )

    assert result.status == ApprovalStatus.APPROVED
    assert result.approved is True
    assert repository.saved == (
        PULL_REQUEST_ID,
        ApprovalStatus.APPROVED,
        "Reviewed and approved.",
    )


@pytest.mark.asyncio
async def test_reject_pending_request() -> None:
    repository = FakeApprovalRepository()
    service = ApprovalService(repository)

    result = await service.decide(
        ApprovalDecision(
            pull_request_id=PULL_REQUEST_ID,
            status=ApprovalStatus.REJECTED,
            reason="Please add more tests.",
        )
    )

    assert result.status == ApprovalStatus.REJECTED
    assert result.rejected is True


@pytest.mark.asyncio
async def test_approved_request_passes_require_approval() -> None:
    repository = FakeApprovalRepository(ApprovalStatus.APPROVED)
    service = ApprovalService(repository)

    result = await service.require_approval(PULL_REQUEST_ID)

    assert result.approved is True


@pytest.mark.asyncio
async def test_pending_request_cannot_pass_approval_gate() -> None:
    repository = FakeApprovalRepository(ApprovalStatus.PENDING)
    service = ApprovalService(repository)

    with pytest.raises(ApprovalRequiredError):
        await service.require_approval(PULL_REQUEST_ID)


@pytest.mark.asyncio
async def test_rejected_request_cannot_pass_approval_gate() -> None:
    repository = FakeApprovalRepository(ApprovalStatus.REJECTED)
    service = ApprovalService(repository)

    with pytest.raises(ApprovalRequiredError):
        await service.require_approval(PULL_REQUEST_ID)


@pytest.mark.asyncio
async def test_approved_request_cannot_be_reapproved() -> None:
    repository = FakeApprovalRepository(ApprovalStatus.APPROVED)
    service = ApprovalService(repository)

    with pytest.raises(InvalidApprovalTransitionError):
        await service.decide(
            ApprovalDecision(
                pull_request_id=PULL_REQUEST_ID,
                status=ApprovalStatus.APPROVED,
            )
        )


@pytest.mark.asyncio
async def test_approved_request_cannot_be_rejected() -> None:
    repository = FakeApprovalRepository(ApprovalStatus.APPROVED)
    service = ApprovalService(repository)

    with pytest.raises(InvalidApprovalTransitionError):
        await service.decide(
            ApprovalDecision(
                pull_request_id=PULL_REQUEST_ID,
                status=ApprovalStatus.REJECTED,
            )
        )


@pytest.mark.asyncio
async def test_rejected_request_cannot_be_approved() -> None:
    repository = FakeApprovalRepository(ApprovalStatus.REJECTED)
    service = ApprovalService(repository)

    with pytest.raises(InvalidApprovalTransitionError):
        await service.decide(
            ApprovalDecision(
                pull_request_id=PULL_REQUEST_ID,
                status=ApprovalStatus.APPROVED,
            )
        )


@pytest.mark.asyncio
async def test_missing_pull_request_raises() -> None:
    repository = FakeApprovalRepository(None)
    service = ApprovalService(repository)

    with pytest.raises(ApprovalNotFoundError):
        await service.get_status(
            ApprovalRequest(pull_request_id=PULL_REQUEST_ID)
        )


@pytest.mark.asyncio
async def test_missing_pull_request_cannot_be_decided() -> None:
    repository = FakeApprovalRepository(None)
    service = ApprovalService(repository)

    with pytest.raises(ApprovalNotFoundError):
        await service.decide(
            ApprovalDecision(
                pull_request_id=PULL_REQUEST_ID,
                status=ApprovalStatus.APPROVED,
            )
        )
