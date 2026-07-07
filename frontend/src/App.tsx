import { useState } from "react";

import { UploadPage } from "@/features/upload/UploadPage";
import { JobStatusView } from "@/features/jobs/JobStatusView";
import { ThemeToggle } from "@/theme/ThemeToggle";

/**
 * Application shell. A single piece of view state (the active job id) switches
 * between the upload screen and the live job/result screen — no router needed
 * for this focused three-screen flow.
 */
export default function App() {
  const [jobId, setJobId] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <button
            onClick={() => setJobId(null)}
            className="focus-ring flex items-center gap-2 rounded-lg font-semibold"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-fg">
              ◆
            </span>
            <span>SheryMeet - Meeting Intelligence</span>
          </button>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        {jobId ? (
          <JobStatusView jobId={jobId} onReset={() => setJobId(null)} />
        ) : (
          <UploadPage onCreated={setJobId} />
        )}
      </main>
    </div>
  );
}
