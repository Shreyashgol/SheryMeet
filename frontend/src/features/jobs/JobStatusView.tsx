import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { getJob, TERMINAL_STATUSES } from "@/api/jobs";
import type { JobStatus } from "@/api/jobs";
import { Button, Card, ProgressBar, StatusPill, cx } from "@/components/ui";
import { PIPELINE_STEPS, statusIndex, statusLabel, statusTone } from "@/lib/status";
import { updateJob } from "@/lib/history";
import { ResultView } from "@/features/result/ResultView";

/**
 * Live job view. Polls the status endpoint until the job reaches a terminal
 * state, showing a stage stepper and progress bar; renders the result on
 * COMPLETED and an error panel on FAILED.
 */
export function JobStatusView({ jobId, onReset }: { jobId: string; onReset: () => void }) {
  const { data, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    // Poll every second while the job is in flight; stop once terminal.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && TERMINAL_STATUSES.includes(status) ? false : 1000;
    },
  });

  // Keep this device's history in sync with the job's live status.
  const status = data?.status;
  useEffect(() => {
    if (status) updateJob(jobId, { status });
  }, [jobId, status]);

  if (error) {
    return (
      <Panel onReset={onReset}>
        <p className="text-danger">Could not load this job. It may not exist.</p>
      </Panel>
    );
  }

  if (!data) {
    return (
      <Panel onReset={onReset}>
        <p className="text-fg-muted">Loading…</p>
      </Panel>
    );
  }

  if (data.status === "COMPLETED") {
    return <ResultView jobId={jobId} onReset={onReset} />;
  }

  const failed = data.status === "FAILED";
  const currentIdx = statusIndex(data.status);

  return (
    <Panel onReset={onReset}>
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">
            {failed ? "Processing failed" : "Processing your meeting"}
          </h2>
          <p className="mt-1 font-mono text-xs text-fg-muted">{jobId}</p>
        </div>
        <StatusPill tone={statusTone(data.status)}>{statusLabel(data.status)}</StatusPill>
      </div>

      {failed ? (
        <div className="rounded-lg bg-danger/10 p-4">
          <p className="text-sm font-medium text-danger">
            Failed at stage: {data.error_stage ?? "unknown"}
          </p>
          {data.error_message && (
            <p className="mt-1 text-sm text-fg-muted">{data.error_message}</p>
          )}
        </div>
      ) : (
        <>
          <ProgressBar value={data.progress} />
          <ol className="mt-6 space-y-3">
            {PIPELINE_STEPS.filter((s) => s.key !== "COMPLETED").map((step) => {
              const idx = statusIndex(step.key as JobStatus);
              const done = idx < currentIdx;
              const active = step.key === data.status;
              return (
                <li key={step.key} className="flex items-center gap-3">
                  <span
                    className={cx(
                      "flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold",
                      done && "bg-success/15 text-success",
                      active && "bg-primary text-primary-fg",
                      !done && !active && "bg-muted text-fg-muted",
                    )}
                  >
                    {done ? "✓" : active ? "•" : ""}
                  </span>
                  <span className={cx("text-sm", active ? "font-medium text-fg" : "text-fg-muted")}>
                    {step.label}
                  </span>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </Panel>
  );
}

function Panel({ children, onReset }: { children: React.ReactNode; onReset: () => void }) {
  return (
    <div className="mx-auto max-w-2xl animate-fade-in">
      <Card>{children}</Card>
      <div className="mt-4 text-center">
        <Button variant="ghost" onClick={onReset}>
          ← Process another meeting
        </Button>
      </div>
    </div>
  );
}
