"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getJob, getJobEventsUrl } from "./api";
import type {
  BackgroundJob,
  JobEvent,
  JobEventType,
  JobStatus,
} from "./types";

interface UseJobEventsResult {
  job: BackgroundJob | null;
  events: JobEvent[];
  status: JobStatus | "connecting" | "error";
  error: string | null;
  connected: boolean;
}

const TERMINAL_STATUSES: JobStatus[] = [
  "succeeded",
  "failed",
];

function parseEvent(
  event: MessageEvent<string>,
): JobEvent {
  return JSON.parse(event.data) as JobEvent;
}

export function useJobEvents(
  jobId: string | null,
): UseJobEventsResult {
  const [job, setJob] = useState<BackgroundJob | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [status, setStatus] = useState<
    JobStatus | "connecting" | "error"
  >("connecting");
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  const eventSourceRef =
    useRef<EventSource | null>(null);

  const closeConnection = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    const currentJobId = jobId;
    let cancelled = false;

    async function refreshJob() {
      try {
        const refreshedJob = await getJob(currentJobId);

        if (!cancelled) {
          setJob(refreshedJob);
          setStatus(refreshedJob.status);
        }
      } catch {
        // The event stream remains the source of live
        // activity even if the final state refresh fails.
      }
    }

    async function start() {
      try {
        const currentJob = await getJob(currentJobId);

        if (cancelled) {
          return;
        }

        setJob(currentJob);
        setStatus(currentJob.status);
        setError(null);

        if (
          TERMINAL_STATUSES.includes(
            currentJob.status,
          )
        ) {
          return;
        }

        const eventSource = new EventSource(
          getJobEventsUrl(currentJobId),
        );

        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          if (cancelled) {
            return;
          }

          setConnected(true);
          setError(null);
        };

        const handleJobEvent = (
          event: MessageEvent<string>,
        ) => {
          if (cancelled) {
            return;
          }

          const parsed = parseEvent(event);

          setEvents((previous) => {
            if (
              previous.some(
                (item) =>
                  item.stream_id === parsed.stream_id,
              )
            ) {
              return previous;
            }

            return [...previous, parsed];
          });

          const nextStatus = statusFromEvent(
            parsed.event_type,
          );

          if (nextStatus) {
            setStatus(nextStatus);
          }

          if (
            parsed.event_type === "job.succeeded" ||
            parsed.event_type === "job.failed"
          ) {
            void refreshJob();
            eventSource.close();
            setConnected(false);
          }
        };

        const eventTypes: JobEventType[] = [
          "job.queued",
          "job.started",
          "job.progress",
          "job.retrying",
          "job.succeeded",
          "job.failed",
        ];

        for (const eventType of eventTypes) {
          eventSource.addEventListener(
            eventType,
            handleJobEvent,
          );
        }

        eventSource.onerror = () => {
          if (cancelled) {
            return;
          }

          setConnected(false);

          if (
            eventSource.readyState ===
            EventSource.CLOSED
          ) {
            setStatus("error");
            setError(
              "The live job connection closed unexpectedly.",
            );
          }
        };
      } catch (cause) {
        if (cancelled) {
          return;
        }

        setStatus("error");
        setError(
          cause instanceof Error
            ? cause.message
            : "Failed to connect to the job.",
        );
      }
    }

    void start();

    return () => {
      cancelled = true;
      closeConnection();
      setConnected(false);
    };
  }, [jobId, closeConnection]);

  return {
    job,
    events,
    status,
    error,
    connected,
  };
}

function statusFromEvent(
  eventType: JobEventType,
): JobStatus | null {
  switch (eventType) {
    case "job.queued":
      return "queued";

    case "job.started":
      return "running";

    case "job.retrying":
      return "retrying";

    case "job.succeeded":
      return "succeeded";

    case "job.failed":
      return "failed";

    case "job.progress":
      return null;
  }
}
