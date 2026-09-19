from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from agents.jobs.queue import RedisJobQueue
from agents.jobs.service import JobService
from apps.api.app.core.database import get_db
from apps.api.app.core.redis import get_redis
from apps.api.app.schemas.orchestration import OrchestrationStartResponse
from apps.api.app.services.task import get_task

router = APIRouter(
    prefix="/tasks",
    tags=["orchestration"],
)


@router.post(
    "/{task_id}/run",
    response_model=OrchestrationStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_orchestration(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> OrchestrationStartResponse:
    task = await get_task(
        session,
        task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} was not found.",
        )

    queue = RedisJobQueue(redis)

    job_service = JobService(
        queue=queue,
        session=session,
    )

    job = await job_service.enqueue_orchestration(
        task_id,
    )

    return OrchestrationStartResponse(
        task_id=task_id,
        status=task.status,
        message=f"Orchestration queued. Job ID: {job.id}.",
    )
