from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskStatusUpdate,
)
from apps.api.app.services.task import (
    create_task,
    get_task,
    list_tasks,
    update_task_status,
)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_endpoint(
    data: TaskCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    try:
        task = await create_task(session, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return TaskResponse.model_validate(task)


@router.get(
    "",
    response_model=list[TaskResponse],
)
async def list_tasks_endpoint(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[TaskResponse]:
    tasks = await list_tasks(session)

    return [
        TaskResponse.model_validate(task)
        for task in tasks
    ]


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
async def get_task_endpoint(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    task = await get_task(session, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
)
async def update_task_status_endpoint(
    task_id: UUID,
    data: TaskStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    task = await update_task_status(
        session,
        task_id,
        data.status,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return TaskResponse.model_validate(task)
