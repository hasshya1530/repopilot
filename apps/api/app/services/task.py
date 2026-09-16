from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
from apps.api.app.schemas.task import TaskCreate


async def create_task(
    session: AsyncSession,
    data: TaskCreate,
) -> Task:
    repository = await session.get(Repository, data.repository_id)

    if repository is None:
        raise ValueError("Repository not found")

    task = Task(
        repository_id=data.repository_id,
        external_issue_id=data.external_issue_id,
        issue_number=data.issue_number,
        title=data.title,
        description=data.description,
        status=TaskStatus.PENDING,
    )

    session.add(task)
    await session.commit()
    await session.refresh(task)

    return task


async def get_task(
    session: AsyncSession,
    task_id: UUID,
) -> Task | None:
    result = await session.execute(select(Task).where(Task.id == task_id))

    return result.scalar_one_or_none()


async def update_task_status(
    session: AsyncSession,
    task_id: UUID,
    status: TaskStatus,
) -> Task | None:
    task = await get_task(session, task_id)

    if task is None:
        return None

    task.status = status

    await session.commit()
    await session.refresh(task)

    return task
