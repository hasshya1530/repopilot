from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.pull_request import ApprovalStatus, PullRequest


class SQLAlchemyApprovalRepository:
    """Persists human approval decisions using PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_approval_status(
        self,
        pull_request_id: UUID,
    ) -> ApprovalStatus | None:
        result = await self._session.execute(
            select(PullRequest.approval_status).where(
                PullRequest.id == pull_request_id
            )
        )

        return result.scalar_one_or_none()

    async def set_approval_status(
        self,
        pull_request_id: UUID,
        status: ApprovalStatus,
        reason: str | None,
        expected_status: ApprovalStatus,
    ) -> bool:
        del reason

        result = await self._session.execute(
            select(PullRequest)
            .where(PullRequest.id == pull_request_id)
            .with_for_update()
        )
        pull_request = result.scalar_one_or_none()

        if pull_request is None:
            return False

        if pull_request.approval_status != expected_status:
            await self._session.rollback()
            return False

        pull_request.approval_status = status

        await self._session.commit()

        return True
