import { useState } from "react";

import { UploadPage } from "@/features/upload/UploadPage";
import { JobStatusView } from "@/features/jobs/JobStatusView";
import { HowToUseModal } from "@/features/help/HowToUseModal";
import { HistoryPanel } from "@/features/history/HistoryPanel";
import { ThemeToggle } from "@/theme/ThemeToggle";
import { recordJob, useHistory } from "@/lib/history";

/**
 * Application shell. A single piece of view state (the active job id) switches
 * between the upload screen and the live job/result screen — no router needed
 * for this focused three-screen flow. Help and History open as overlays.
 */
export default function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const history = useHistory();

  const handleCreated = (id: string, filename: string) => {
    recordJob(id, filename);
    setJobId(id);
  };

  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-6 py-3">
          <button
            onClick={() => setJobId(null)}
            className="focus-ring flex items-center gap-2 rounded-lg font-semibold"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-fg">
              ◆
            </span>
            <span className="hidden sm:inline">SheryMeet - Meeting Intelligence</span>
            <span className="sm:hidden">SheryMeet</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setHelpOpen(true)}
              className="focus-ring inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-medium text-fg transition-colors hover:bg-muted"
            >
              <span aria-hidden>?</span>
              <span className="hidden sm:inline">How to use</span>
            </button>
            <button
              onClick={() => setHistoryOpen(true)}
              className="focus-ring inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-medium text-fg transition-colors hover:bg-muted"
            >
              <span aria-hidden>◷</span>
              <span className="hidden sm:inline">History</span>
              {history.length > 0 && (
                <span className="ml-0.5 inline-flex min-w-5 items-center justify-center rounded-full bg-primary/15 px-1.5 text-xs font-semibold text-primary">
                  {history.length}
                </span>
              )}
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        {jobId ? (
          <JobStatusView jobId={jobId} onReset={() => setJobId(null)} />
        ) : (
          <UploadPage onCreated={handleCreated} />
        )}
      </main>

      <HowToUseModal open={helpOpen} onClose={() => setHelpOpen(false)} />
      <HistoryPanel
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onOpen={setJobId}
      />
    </div>
  );
}
