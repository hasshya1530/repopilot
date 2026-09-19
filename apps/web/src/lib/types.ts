export type JobStatus =
  | "queued"
  | "running"
  | "retrying"
  | "succeeded"
  | "failed";

export type JobEventType =
  | "job.queued"
  | "job.started"
  | "job.progress"
  | "job.retrying"
  | "job.succeeded"
  | "job.failed";

export interface BackgroundJob {
  id: string;
  task_id: string;
  job_type: string;
  status: JobStatus;
  attempt: number;
  max_attempts: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobEvent {
  stream_id: string;
  event_id: string;
  job_id: string;
  task_id: string;
  event_type: JobEventType;
  message: string;
  attempt: number;
  created_at: string;
  metadata: Record<string, unknown>;
}
