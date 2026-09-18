from typing import Protocol
from uuid import UUID

from agents.approval.errors import (
    ApprovalNotFoundError,
    ApprovalRequiredError,
    InvalidApprovalTransitionError,
)
from agents.approval.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalResult,
)
from apps.api.app.models.pull_request import ApprovalStatus


class PullRequestApprovalRepository(Protocol):
    async def get_approval_status(
        self,
        pull_request_id: UUID,
    ) -> ApprovalStatus | None:
        """Return the current approval status."""

    async def set_approval_status(
        self,
        pull_request_id: UUID,
        status: ApprovalStatus,
        reason: str | None,
        expected_status: ApprovalStatus,
    ) -> bool:
        """Persist a decision if the expected current state is unchanged."""


class ApprovalService:
    """Controls the human approval boundary before PR creation."""

    def __init__(
        self,
        repository: PullRequestApprovalRepository,
    ) -> None:
        self._repository = repository

    async def get_status(
        self,
        request: ApprovalRequest,
    ) -> ApprovalResult:
        status = await self._repository.get_approval_status(
            request.pull_request_id
        )

        if status is None:
            raise ApprovalNotFoundError(
                f"Pull request {request.pull_request_id} was not found."
            )

        return ApprovalResult(
            pull_request_id=request.pull_request_id,
            status=status,
        )

    async def decide(
        self,
        decision: ApprovalDecision,
    ) -> ApprovalResult:
        current_status = await self._repository.get_approval_status(
            decision.pull_request_id
        )

        if current_status is None:
            raise ApprovalNotFoundError(
                f"Pull request {decision.pull_request_id} was not found."
            )

        self._validate_transition(
            current_status=current_status,
            requested_status=decision.status,
        )

        persisted = await self._repository.set_approval_status(
            decision.pull_request_id,
            decision.status,
            decision.reason,
            current_status,
        )

        if not persisted:
            raise InvalidApprovalTransitionError(
                "Approval changed before the decision could be persisted."
            )

        return ApprovalResult(
            pull_request_id=decision.pull_request_id,
            status=decision.status,
            reason=decision.reason,
        )

    async def require_approval(
        self,
        pull_request_id: UUID,
    ) -> ApprovalResult:
        result = await self.get_status(
            ApprovalRequest(pull_request_id=pull_request_id)
        )

        if not result.approved:
            raise ApprovalRequiredError(
                f"Human approval is required for pull request "
                f"{pull_request_id}; current status is "
                f"{result.status.value}."
            )

        return result

    @staticmethod
    def _validate_transition(
        *,
        current_status: ApprovalStatus,
        requested_status: ApprovalStatus,
    ) -> None:
        if current_status == ApprovalStatus.PENDING:
            if requested_status in {
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
            }:
                return

        raise InvalidApprovalTransitionError(
            f"Cannot transition approval from "
            f"{current_status.value!r} to "
            f"{requested_status.value!r}."
        )
