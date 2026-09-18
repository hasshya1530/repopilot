from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
from apps.api.app.services.repository import get_repository
from apps.api.app.services.task import get_task, update_task_status


class SqlAlchemyTaskPersistence:
    """Persistence adapter backed by the existing application services."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_task(
        self,
        task_id: UUID,
    ) -> Task | None:
        return await get_task(
            self._session,
            task_id,
        )

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
    ) -> Task | None:
        return await update_task_status(
            self._session,
            task_id,
            status,
        )

    async def get_repository(
        self,
        repository_id: UUID,
    ) -> Repository | None:
        return await get_repository(
            self._session,
            repository_id,
        )
