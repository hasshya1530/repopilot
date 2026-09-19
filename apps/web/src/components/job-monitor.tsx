"use client";

import { FormEvent, useState } from "react";

import { runTask } from "@/lib/api";
import { useJobEvents } from "@/lib/use-job-events";
import type { JobEvent } from "@/lib/types";

interface JobMonitorProps {
  initialTaskId?: string;
}

function formatEventType(eventType: string): string {
  return eventType
    .replace("job.", "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString();
}

function statusClasses(status: string): string {
  switch (status) {
    case "succeeded":
      return "bg-emerald-100 text-emerald-700";
    case "failed":
      return "bg-red-100 text-red-700";
    case "running":
      return "bg-blue-100 text-blue-700";
    case "retrying":
      return "bg-amber-100 text-amber-700";
    case "queued":
      return "bg-zinc-100 text-zinc-700";
    default:
      return "bg-zinc-100 text-zinc-700";
  }
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-semibold text-zinc-950 dark:text-zinc-50">
        {value}
      </p>
    </div>
  );
}

function EventRow({ event }: { event: JobEvent }) {
  return (
    <div className="flex gap-4 border-b border-zinc-100 py-4 last:border-b-0 dark:border-zinc-800">
      <div className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-zinc-400" />

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {formatEventType(event.event_type)}
          </span>

          <span className="text-xs text-zinc-400">
            attempt {event.attempt}
          </span>

          <span className="text-xs text-zinc-400">
            {formatTimestamp(event.created_at)}
          </span>
        </div>

        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          {event.message}
        </p>
      </div>
    </div>
  );
}

export function JobMonitor({ initialTaskId = "" }: JobMonitorProps) {
  const [taskId, setTaskId] = useState(initialTaskId);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const {
    job,
    events,
    status,
    error: monitorError,
    connected,
  } = useJobEvents(activeJobId);

  async function handleRunTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedTaskId = taskId.trim();

    if (!normalizedTaskId) {
      setRunError("Enter a task UUID.");
      return;
    }

    setRunError(null);
    setStarting(true);
    setActiveJobId(null);

    try {
      const createdJob = await runTask(normalizedTaskId);
      setActiveJobId(createdJob.id);
    } catch (error) {
      setRunError(
        error instanceof Error
          ? error.message
          : "Failed to start the task.",
      );
    } finally {
      setStarting(false);
    }
  }

  const displayStatus = job?.status ?? status ?? "idle";
  const error = runError ?? monitorError;

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <div>
          <h2 className="text-lg font-semibold text-zinc-950 dark:text-zinc-50">
            Run a RepoPilot task
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Start a background agent job and watch its execution in real time.
          </p>
        </div>

        <form
          onSubmit={handleRunTask}
          className="mt-5 flex flex-col gap-3 sm:flex-row"
        >
          <input
            value={taskId}
            onChange={(event) => setTaskId(event.target.value)}
            placeholder="Task UUID"
            className="h-11 flex-1 rounded-xl border border-zinc-300 bg-white px-4 text-sm text-zinc-900 outline-none transition focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:focus:ring-zinc-800"
            disabled={starting}
          />

          <button
            type="submit"
            disabled={starting || !taskId.trim()}
            className="h-11 rounded-xl bg-zinc-950 px-5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-950 dark:hover:bg-zinc-200"
          >
            {starting ? "Starting..." : "Run Task"}
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      {activeJobId && (
        <>
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                  Active background job
                </p>

                <p className="mt-1 break-all font-mono text-sm text-zinc-900 dark:text-zinc-100">
                  {activeJobId}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium ${statusClasses(
                    displayStatus,
                  )}`}
                >
                  {displayStatus}
                </span>

                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    connected
                      ? "bg-emerald-500"
                      : "bg-zinc-300 dark:bg-zinc-700"
                  }`}
                />

                <span className="text-xs text-zinc-500">
                  {connected ? "Live" : "Disconnected"}
                </span>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-4">
              <Stat
                label="Status"
                value={job?.status ?? displayStatus}
              />

              <Stat
                label="Attempt"
                value={
                  job
                    ? `${job.attempt}/${job.max_attempts}`
                    : "—"
                }
              />

              <Stat
                label="Type"
                value={job?.job_type ?? "orchestration"}
              />

              <Stat
                label="Events"
                value={events.length}
              />
            </div>

            {job?.error_message && (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
                <p className="text-xs font-medium uppercase tracking-wide text-red-500">
                  Job error
                </p>
                <p className="mt-1 text-sm text-red-700">
                  {job.error_message}
                </p>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-zinc-950 dark:text-zinc-50">
                  Live activity
                </h2>

                <p className="mt-1 text-sm text-zinc-500">
                  Events emitted by the RepoPilot worker.
                </p>
              </div>

              <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
                {events.length} events
              </span>
            </div>

            <div className="mt-4">
              {events.length === 0 ? (
                <div className="rounded-xl border border-dashed border-zinc-300 px-4 py-10 text-center text-sm text-zinc-500 dark:border-zinc-700">
                  Waiting for worker events...
                </div>
              ) : (
                events.map((event) => (
                  <EventRow
                    key={event.stream_id}
                    event={event}
                  />
                ))
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
