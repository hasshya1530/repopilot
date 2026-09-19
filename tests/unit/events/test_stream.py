from uuid import uuid4

import pytest

from agents.events.models import JobEvent, JobEventType
from agents.events.stream import RedisJobEventStream


class FakeRedis:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str, dict[str, str]]] = []
        self.deleted: list[str] = []

    async def xadd(
        self,
        stream: str,
        fields: dict[str, str],
        *,
        maxlen: int,
        approximate: bool,
    ) -> str:
        assert maxlen == 1000
        assert approximate is True

        entry_id = f"{len(self.entries) + 1}-0"

        self.entries.append(
            (
                stream,
                entry_id,
                fields,
            )
        )

        return entry_id

    async def xread(
        self,
        streams: dict[str, str],
        *,
        count: int,
        block: int,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
        assert count == 100
        assert block == 5000

        stream_name, last_id = next(iter(streams.items()))

        def is_after(entry_id: str) -> bool:
            if last_id == "$":
                return False

            last_sequence = int(last_id.split("-", 1)[0])
            entry_sequence = int(entry_id.split("-", 1)[0])

            return entry_sequence > last_sequence

        matching = [
            (entry_id, fields)
            for name, entry_id, fields in self.entries
            if name == stream_name and is_after(entry_id)
        ]

        if not matching:
            return []

        return [
            (
                stream_name,
                matching,
            )
        ]

    async def delete(self, stream: str) -> int:
        self.deleted.append(stream)
        return 1


def make_event(
    *,
    job_id,
    task_id,
    event_type: JobEventType,
    message: str,
) -> JobEvent:
    return JobEvent.create(
        event_id=uuid4(),
        job_id=job_id,
        task_id=task_id,
        event_type=event_type,
        message=message,
        attempt=0,
    )


@pytest.mark.asyncio
async def test_publish_and_read_event() -> None:
    redis = FakeRedis()
    stream = RedisJobEventStream(redis)

    job_id = uuid4()
    task_id = uuid4()

    event = make_event(
        job_id=job_id,
        task_id=task_id,
        event_type=JobEventType.STARTED,
        message="Worker started",
    )

    entry_id = await stream.publish(event)

    assert entry_id == "1-0"

    events = await stream.read(str(job_id))

    assert len(events) == 1
    assert events[0]["stream_id"] == "1-0"
    assert events[0]["event_type"] == "job.started"
    assert events[0]["message"] == "Worker started"
    assert events[0]["attempt"] == 0
    assert events[0]["metadata"] == {}


@pytest.mark.asyncio
async def test_read_replays_all_events_from_beginning() -> None:
    redis = FakeRedis()
    stream = RedisJobEventStream(redis)

    job_id = uuid4()
    task_id = uuid4()

    await stream.publish(
        make_event(
            job_id=job_id,
            task_id=task_id,
            event_type=JobEventType.STARTED,
            message="Started",
        )
    )

    await stream.publish(
        make_event(
            job_id=job_id,
            task_id=task_id,
            event_type=JobEventType.SUCCEEDED,
            message="Succeeded",
        )
    )

    events = await stream.read(
        str(job_id),
        last_id="0-0",
    )

    assert len(events) == 2
    assert events[0]["stream_id"] == "1-0"
    assert events[1]["stream_id"] == "2-0"


@pytest.mark.asyncio
async def test_read_replays_only_events_after_last_id() -> None:
    redis = FakeRedis()
    stream = RedisJobEventStream(redis)

    job_id = uuid4()
    task_id = uuid4()

    await stream.publish(
        make_event(
            job_id=job_id,
            task_id=task_id,
            event_type=JobEventType.STARTED,
            message="Started",
        )
    )

    await stream.publish(
        make_event(
            job_id=job_id,
            task_id=task_id,
            event_type=JobEventType.PROGRESS,
            message="Progress",
        )
    )

    await stream.publish(
        make_event(
            job_id=job_id,
            task_id=task_id,
            event_type=JobEventType.SUCCEEDED,
            message="Succeeded",
        )
    )

    events = await stream.read(
        str(job_id),
        last_id="1-0",
    )

    assert len(events) == 2
    assert events[0]["stream_id"] == "2-0"
    assert events[1]["stream_id"] == "3-0"


@pytest.mark.asyncio
async def test_read_after_latest_event_returns_empty() -> None:
    redis = FakeRedis()
    stream = RedisJobEventStream(redis)

    job_id = uuid4()
    task_id = uuid4()

    await stream.publish(
        make_event(
            job_id=job_id,
            task_id=task_id,
            event_type=JobEventType.SUCCEEDED,
            message="Succeeded",
        )
    )

    events = await stream.read(
        str(job_id),
        last_id="1-0",
    )

    assert events == []


@pytest.mark.asyncio
async def test_read_does_not_mix_job_streams() -> None:
    redis = FakeRedis()
    stream = RedisJobEventStream(redis)

    job_id = uuid4()
    other_job_id = uuid4()
    task_id = uuid4()

    await stream.publish(
        make_event(
            job_id=job_id,
            task_id=task_id,
            event_type=JobEventType.STARTED,
            message="Job one",
        )
    )

    await stream.publish(
        make_event(
            job_id=other_job_id,
            task_id=task_id,
            event_type=JobEventType.STARTED,
            message="Job two",
        )
    )

    events = await stream.read(str(job_id))

    assert len(events) == 1
    assert events[0]["message"] == "Job one"


@pytest.mark.asyncio
async def test_delete_stream() -> None:
    redis = FakeRedis()
    stream = RedisJobEventStream(redis)

    job_id = uuid4()

    result = await stream.delete(str(job_id))

    assert result == 1
    assert redis.deleted == [
        f"repopilot:events:job:{job_id}"
    ]
