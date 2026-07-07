import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { getJobResult } from "@/api/jobs";
import type { JobResult } from "@/api/jobs";
import { Button, Card, EmptyList, PriorityBadge, StatusPill } from "@/components/ui";
import { updateJob } from "@/lib/history";

/** Renders the completed meeting result: summary sections + accountable checklist. */
export function ResultView({ jobId, onReset }: { jobId: string; onReset: () => void }) {
  const { data, error } = useQuery({
    queryKey: ["result", jobId],
    queryFn: () => getJobResult(jobId),
  });

  // Replace the placeholder (filename) with the AI-generated meeting title in
  // this device's history once the result is available.
  const meetingTitle = data?.summary.meeting_title;
  useEffect(() => {
    if (meetingTitle) updateJob(jobId, { title: meetingTitle, status: "COMPLETED" });
  }, [jobId, meetingTitle]);

  if (error) {
    return (
      <Wrapper onReset={onReset}>
        <Card>
          <p className="text-danger">Could not load the result.</p>
        </Card>
      </Wrapper>
    );
  }
  if (!data) {
    return (
      <Wrapper onReset={onReset}>
        <Card>
          <p className="text-fg-muted">Loading result…</p>
        </Card>
      </Wrapper>
    );
  }

  return (
    <Wrapper onReset={onReset}>
      <div className="space-y-5">
        <Header data={data} />
        <ChecklistCard items={data.checklist} />
        <div className="grid gap-5 md:grid-cols-2">
          <ListCard title="Agenda" items={data.summary.agenda} />
          <ListCard title="Key decisions" items={data.summary.key_decisions} />
          <ListCard title="Risks" items={data.summary.risks} />
          <ListCard title="Blockers" items={data.summary.blockers} />
        </div>
        <ListCard title="Next steps" items={data.summary.next_steps} />
        <MetadataCard data={data} />
      </div>
    </Wrapper>
  );
}

function Header({ data }: { data: JobResult }) {
  return (
    <Card>
      <div className="mb-3 flex items-start justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">{data.summary.meeting_title}</h1>
        <StatusPill tone="success">Completed</StatusPill>
      </div>
      <p className="leading-relaxed text-fg-muted">{data.summary.summary}</p>
    </Card>
  );
}

function ChecklistCard({ items }: { items: JobResult["checklist"] }) {
  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Accountable checklist</h2>
        <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-fg-muted">
          {items.length} {items.length === 1 ? "item" : "items"}
        </span>
      </div>
      {items.length === 0 ? (
        <EmptyList>No action items were identified.</EmptyList>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase tracking-wide text-fg-muted">
                <th className="pb-2 pr-4 font-medium">Task</th>
                <th className="pb-2 pr-4 font-medium">Owner</th>
                <th className="pb-2 pr-4 font-medium">Deadline</th>
                <th className="pb-2 pr-4 font-medium">Priority</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-border/60 last:border-0">
                  <td className="py-3 pr-4 font-medium">{item.task}</td>
                  <td className="py-3 pr-4 text-fg-muted">{item.owner}</td>
                  <td className="py-3 pr-4 text-fg-muted">{item.deadline}</td>
                  <td className="py-3 pr-4">
                    <PriorityBadge priority={item.priority} />
                  </td>
                  <td className="py-3 text-fg-muted">{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-fg-muted">{title}</h3>
      {items.length === 0 ? (
        <EmptyList>None.</EmptyList>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2 text-sm">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function MetadataCard({ data }: { data: JobResult }) {
  const m = data.metadata;
  const seconds = (ms: number) => `${(ms / 1000).toFixed(1)}s`;
  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-fg-muted">
        Processing metadata
      </h3>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
        <Meta label="Model" value={`${m.llm_provider} · ${m.llm_model}`} />
        <Meta label="Language" value={m.language ?? "—"} />
        <Meta
          label="Duration"
          value={m.duration_seconds != null ? `${m.duration_seconds.toFixed(0)}s` : "—"}
        />
        {Object.entries(m.latencies_ms).map(([stage, ms]) => (
          <Meta key={stage} label={stage.toLowerCase()} value={seconds(ms)} />
        ))}
        {m.total_pipeline_ms != null && (
          <Meta label="total pipeline" value={seconds(m.total_pipeline_ms)} />
        )}
      </dl>
    </Card>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-fg-muted">{label}</dt>
      <dd className="mt-0.5 font-medium">{value}</dd>
    </div>
  );
}

function Wrapper({ children, onReset }: { children: React.ReactNode; onReset: () => void }) {
  return (
    <div className="mx-auto max-w-3xl animate-fade-in">
      {children}
      <div className="mt-6 text-center">
        <Button variant="ghost" onClick={onReset}>
          ← Process another meeting
        </Button>
      </div>
    </div>
  );
}
