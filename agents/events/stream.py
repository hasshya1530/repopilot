import json
from typing import Any

from redis.asyncio import Redis

from agents.events.models import JobEvent


class RedisJobEventStream:
    def __init__(
        self,
        redis: Redis,
        *,
        stream_prefix: str = "repopilot:events:job",
        max_length: int = 1000,
    ) -> None:
        self._redis = redis
        self._stream_prefix = stream_prefix
        self._max_length = max_length

    def stream_name(self, job_id: str) -> str:
        return f"{self._stream_prefix}:{job_id}"

    async def publish(self, event: JobEvent) -> str:
        payload = event.to_dict()

        fields: dict[str, str] = {
            "event_id": str(payload["event_id"]),
            "job_id": str(payload["job_id"]),
            "task_id": str(payload["task_id"]),
            "event_type": str(payload["event_type"]),
            "message": str(payload["message"]),
            "attempt": str(payload["attempt"]),
            "created_at": str(payload["created_at"]),
            "metadata": json.dumps(payload["metadata"] or {}),
        }

        entry_id = await self._redis.xadd(
            self.stream_name(str(event.job_id)),
            fields,  # type: ignore[arg-type]
            maxlen=self._max_length,
            approximate=True,
        )

        if isinstance(entry_id, bytes):
            return entry_id.decode("utf-8")

        return str(entry_id)

    async def read(
        self,
        job_id: str,
        *,
        last_id: str = "0-0",
        count: int = 100,
        block_ms: int = 5000,
    ) -> list[dict[str, Any]]:
        result = await self._redis.xread(
            {self.stream_name(job_id): last_id},
            count=count,
            block=block_ms,
        )

        events: list[dict[str, Any]] = []

        for stream_result in result:
            if not isinstance(stream_result, (list, tuple)):
                continue

            if len(stream_result) != 2:
                continue

            stream_entries = stream_result[1]

            if not isinstance(stream_entries, (list, tuple)):
                continue

            for entry in stream_entries:
                if not isinstance(entry, (list, tuple)):
                    continue

                if len(entry) != 2:
                    continue

                entry_id = entry[0]
                fields = entry[1]

                if isinstance(entry_id, bytes):
                    entry_id = entry_id.decode("utf-8")

                if not isinstance(fields, dict):
                    continue

                decoded: dict[str, Any] = {
                    "stream_id": str(entry_id),
                }

                for key, value in fields.items():
                    if isinstance(key, bytes):
                        decoded_key = key.decode("utf-8")
                    else:
                        decoded_key = str(key)

                    if isinstance(value, bytes):
                        decoded_value: Any = value.decode("utf-8")
                    else:
                        decoded_value = value

                    decoded[decoded_key] = decoded_value

                if "attempt" in decoded:
                    decoded["attempt"] = int(decoded["attempt"])

                if "metadata" in decoded:
                    metadata_value = decoded["metadata"]

                    if isinstance(metadata_value, str):
                        decoded["metadata"] = json.loads(metadata_value)

                events.append(decoded)

        return events

    async def delete(self, job_id: str) -> int:
        return int(await self._redis.delete(self.stream_name(job_id)))
