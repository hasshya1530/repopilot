from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from agents.jobs.models import Job, JobType
from agents.jobs.queue import RedisJobQueue
from apps.api.app.services.background_job import (
    create_background_job,
    get_background_job,
)


class JobService:
    """Application service for creating and enqueueing background jobs."""

    def __init__(
        self,
        queue: RedisJobQueue,
        session: AsyncSession,
    ) -> None:
        self._queue = queue
        self._session = session

    async def enqueue_orchestration(
        self,
        task_id: UUID,
        *,
        max_attempts: int = 3,
    ) -> Job:
        job = Job(
            id=uuid4(),
            job_type=JobType.ORCHESTRATION,
            task_id=task_id,
            attempt=0,
            max_attempts=max_attempts,
        )

        await create_background_job(
            self._session,
            job,
        )

        try:
            await self._queue.enqueue(job)
        except Exception:
            background_job = await get_background_job(
                self._session,
                job.id,
            )

            if background_job is not None:
                background_job.status = "failed"
                background_job.error_message = (
                    "Failed to enqueue background job in Redis."
                )
                await self._session.commit()

            raise

        return job
