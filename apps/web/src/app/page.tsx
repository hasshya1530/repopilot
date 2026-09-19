import { JobMonitor } from "@/components/job-monitor";

export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-50 px-6 py-12 dark:bg-black">
      <div className="mx-auto max-w-5xl">
        <header className="mb-10">
          <div className="inline-flex items-center rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-600 shadow-sm dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-400">
            RepoPilot · Agent Runtime
          </div>

          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50 sm:text-5xl">
            Autonomous Software Engineering Agent
          </h1>

          <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-600 dark:text-zinc-400">
            Start a RepoPilot task and watch the agent execute through its
            background job runtime in real time.
          </p>
        </header>

        <JobMonitor />
      </div>
    </main>
  );
}
