from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.jobs.models import Job
from apps.api.app.models.background_job import (
    BackgroundJob,
    BackgroundJobStatus,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def create_background_job(
    session: AsyncSession,
    job: Job,
) -> BackgroundJob:
    background_job = BackgroundJob(
        id=job.id,
        task_id=job.task_id,
        job_type=job.job_type.value,
        status=BackgroundJobStatus.QUEUED,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
    )

    session.add(background_job)
    await session.commit()
    await session.refresh(background_job)

    return background_job


async def get_background_job(
    session: AsyncSession,
    job_id: UUID,
) -> BackgroundJob | None:
    result = await session.execute(
        select(BackgroundJob).where(BackgroundJob.id == job_id)
    )

    return result.scalar_one_or_none()


async def mark_job_running(
    session: AsyncSession,
    job: Job,
) -> BackgroundJob | None:
    background_job = await get_background_job(session, job.id)

    if background_job is None:
        return None

    background_job.status = BackgroundJobStatus.RUNNING
    background_job.attempt = job.attempt
    background_job.started_at = _utcnow()
    background_job.error_message = None

    await session.commit()
    await session.refresh(background_job)

    return background_job


async def mark_job_retrying(
    session: AsyncSession,
    job: Job,
    error_message: str,
) -> BackgroundJob | None:
    background_job = await get_background_job(session, job.id)

    if background_job is None:
        return None

    background_job.status = BackgroundJobStatus.RETRYING
    background_job.attempt = job.next_attempt
    background_job.error_message = error_message

    await session.commit()
    await session.refresh(background_job)

    return background_job


async def mark_job_succeeded(
    session: AsyncSession,
    job: Job,
) -> BackgroundJob | None:
    background_job = await get_background_job(session, job.id)

    if background_job is None:
        return None

    background_job.status = BackgroundJobStatus.SUCCEEDED
    background_job.attempt = job.attempt
    background_job.completed_at = _utcnow()
    background_job.error_message = None

    await session.commit()
    await session.refresh(background_job)

    return background_job


async def mark_job_failed(
    session: AsyncSession,
    job: Job,
    error_message: str,
) -> BackgroundJob | None:
    background_job = await get_background_job(session, job.id)

    if background_job is None:
        return None

    background_job.status = BackgroundJobStatus.FAILED
    background_job.attempt = job.attempt
    background_job.completed_at = _utcnow()
    background_job.error_message = error_message

    await session.commit()
    await session.refresh(background_job)

    return background_job
