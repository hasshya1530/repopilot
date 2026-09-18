
from sqlalchemy.ext.asyncio import AsyncSession

from agents.approval.repository import SQLAlchemyApprovalRepository


def test_repository_can_be_constructed(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyApprovalRepository(db_session)

    assert repository is not None


def test_repository_uses_async_session(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyApprovalRepository(db_session)

    assert isinstance(repository, SQLAlchemyApprovalRepository)
