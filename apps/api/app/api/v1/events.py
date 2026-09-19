import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from agents.events.service import JobEventService
from agents.events.stream import RedisJobEventStream
from apps.api.app.core.redis import get_redis

router = APIRouter(
    prefix="/jobs",
    tags=["job-events"],
)


def create_event_service(redis: Redis) -> JobEventService:
    stream = RedisJobEventStream(redis)
    return JobEventService(stream)


def parse_last_event_id(
    last_event_id: str | None,
) -> str:
    if not last_event_id:
        return "0-0"

    value = last_event_id.strip()

    if not value:
        return "0-0"

    if value == "$":
        return "$"

    parts = value.split("-", 1)

    if (
        len(parts) != 2
        or not parts[0].isdigit()
        or not parts[1].isdigit()
    ):
        return "0-0"

    return value


async def job_event_generator(
    service: JobEventService,
    job_id: UUID,
    *,
    last_event_id: str,
) -> AsyncIterator[str]:
    current_id = parse_last_event_id(last_event_id)

    while True:
        events = await service.read(
            job_id,
            last_id=current_id,
            count=100,
            block_ms=5000,
        )

        if events:
            for event in events:
                stream_id = str(event["stream_id"])
                current_id = stream_id

                event_type = str(
                    event.get(
                        "event_type",
                        "message",
                    )
                )

                payload = json.dumps(
                    event,
                    separators=(",", ":"),
                )

                yield (
                    f"id: {stream_id}\n"
                    f"event: {event_type}\n"
                    f"data: {payload}\n\n"
                )

                if event_type in {
                    "job.succeeded",
                    "job.failed",
                }:
                    return
        else:
            yield ": keep-alive\n\n"

        await asyncio.sleep(0.1)


@router.get(
    "/{job_id}/events",
    response_class=StreamingResponse,
)
async def stream_job_events(
    job_id: UUID,
    redis: Annotated[Redis, Depends(get_redis)],
    last_event_id: Annotated[
        str | None,
        Header(alias="Last-Event-ID"),
    ] = None,
) -> StreamingResponse:
    service = create_event_service(redis)

    return StreamingResponse(
        job_event_generator(
            service,
            job_id,
            last_event_id=last_event_id or "0-0",
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
