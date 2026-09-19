from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from redis.asyncio import Redis

from agents.jobs.models import Job, JobStatus, JobType
from agents.jobs.queue import RedisJobQueue
from agents.jobs.retry import RetryPolicy
from apps.api.app.core.config import get_settings
from apps.api.app.core.database import async_session_factory
from apps.api.app.services.background_job import (
    mark_job_failed,
    mark_job_retrying,
    mark_job_running,
    mark_job_succeeded,
)
from apps.api.app.services.orchestration_factory import create_orchestration_service

logger = logging.getLogger(__name__)


class JobHandler(Protocol):
    async def __call__(self, job: Job) -> None: ...


class JobWorker:
    def __init__(
        self,
        queue: RedisJobQueue,
        *,
        retry_policy: RetryPolicy | None = None,
        poll_timeout: int = 5,
    ) -> None:
        self._queue = queue
        self._retry_policy = retry_policy or RetryPolicy()
        self._poll_timeout = poll_timeout
        self._handlers: dict[str, JobHandler] = {}

    def register_handler(
        self,
        job_type: str,
        handler: JobHandler,
    ) -> None:
        self._handlers[job_type] = handler

    async def _mark_running(self, job: Job) -> None:
        async with async_session_factory() as session:
            await mark_job_running(session, job)

    async def _mark_succeeded(self, job: Job) -> None:
        async with async_session_factory() as session:
            await mark_job_succeeded(session, job)

    async def _mark_retrying(
        self,
        job: Job,
        error_message: str,
    ) -> None:
        async with async_session_factory() as session:
            await mark_job_retrying(
                session,
                job,
                error_message,
            )

    async def _mark_failed(
        self,
        job: Job,
        error_message: str,
    ) -> None:
        async with async_session_factory() as session:
            await mark_job_failed(
                session,
                job,
                error_message,
            )

    async def process_once(self) -> JobStatus | None:
        job = await self._queue.dequeue(
            timeout=self._poll_timeout,
        )

        if job is None:
            return None

        await self._mark_running(job)

        handler = self._handlers.get(
            job.job_type.value,
        )

        if handler is None:
            error_message = (
                f"No handler registered for job type "
                f"{job.job_type.value!r}."
            )

            await self._mark_failed(
                job,
                error_message,
            )

            logger.error(
                "Job %s failed: %s",
                job.id,
                error_message,
            )

            return JobStatus.FAILED

        try:
            await handler(job)

        except Exception as exc:
            error_message = (
                str(exc) or exc.__class__.__name__
            )

            logger.exception(
                "Job %s failed on attempt %d.",
                job.id,
                job.attempt,
            )

            if not job.has_attempts_remaining:
                await self._mark_failed(
                    job,
                    error_message,
                )

                logger.error(
                    "Job %s exhausted all retry attempts.",
                    job.id,
                )

                return JobStatus.FAILED

            await self._mark_retrying(
                job,
                error_message,
            )

            retry_attempt = job.next_attempt
            delay = self._retry_policy.delay_for_attempt(
                retry_attempt,
            )

            if delay > 0:
                await asyncio.sleep(delay)

            retry_job = Job(
                id=job.id,
                job_type=job.job_type,
                task_id=job.task_id,
                attempt=retry_attempt,
                max_attempts=job.max_attempts,
            )

            await self._queue.enqueue(
                retry_job,
            )

            logger.warning(
                "Job %s scheduled for retry %d/%d.",
                job.id,
                retry_attempt,
                job.max_attempts - 1,
            )

            return JobStatus.RETRYING

        await self._mark_succeeded(job)

        return JobStatus.SUCCEEDED

    async def run(self) -> None:
        logger.info("RepoPilot worker started.")

        while True:
            try:
                await self.process_once()
            except asyncio.CancelledError:
                logger.info("RepoPilot worker shutting down.")
                raise
            except Exception:
                logger.exception(
                    "Unexpected worker-loop error. Continuing."
                )
                await asyncio.sleep(1)


async def run_orchestration_job(job: Job) -> None:
    async with async_session_factory() as session:
        service = create_orchestration_service(session)

        await service.run(
            job.task_id,
        )


async def main() -> None:
    settings = get_settings()

    redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=5,
        socket_timeout=None,
    )

    queue = RedisJobQueue(redis)

    worker = JobWorker(queue)

    worker.register_handler(
        JobType.ORCHESTRATION.value,
        run_orchestration_job,
    )

    try:
        await worker.run()
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
