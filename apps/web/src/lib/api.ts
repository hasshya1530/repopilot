import type { BackgroundJob } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function parseError(response: Response): Promise<Error> {
  let detail = `Request failed with status ${response.status}`;

  try {
    const body = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>;
    };

    if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body.detail)) {
      detail = body.detail
        .map((item) => item.msg)
        .filter(Boolean)
        .join(", ");
    }
  } catch {
    // Keep the HTTP status fallback.
  }

  return new Error(detail);
}

export async function getJob(jobId: string): Promise<BackgroundJob> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/jobs/${jobId}`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json() as Promise<BackgroundJob>;
}

export async function runTask(taskId: string): Promise<BackgroundJob> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/tasks/${taskId}/run`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json() as Promise<BackgroundJob>;
}

export function getJobEventsUrl(jobId: string): string {
  return `${API_BASE_URL}/api/v1/jobs/${jobId}/events`;
}
