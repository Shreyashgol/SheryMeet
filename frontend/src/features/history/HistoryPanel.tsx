import { Modal } from "@/components/Modal";
import { StatusPill } from "@/components/ui";
import { statusLabel, statusTone } from "@/lib/status";
import { clearHistory, removeJob, useHistory } from "@/lib/history";

/** Format an ISO timestamp as a compact relative time ("3h ago"). */
function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

/**
 * Past meetings processed on this device. Clicking an entry reopens its job
 * (live status or completed result); the × removes a single entry.
 */
export function HistoryPanel({
  open,
  onClose,
  onOpen,
}: {
  open: boolean;
  onClose: () => void;
  onOpen: (jobId: string) => void;
}) {
  const entries = useHistory();

  return (
    <Modal open={open} onClose={onClose} title="History" wide>
      {entries.length === 0 ? (
        <p className="py-6 text-center text-sm text-fg-muted">
          No meetings yet. Processed meetings will appear here.
        </p>
      ) : (
        <>
          <ul className="-mx-2 max-h-[60vh] space-y-1 overflow-y-auto">
            {entries.map((e) => (
              <li key={e.jobId}>
                <div className="group flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-muted">
                  <button
                    onClick={() => {
                      onOpen(e.jobId);
                      onClose();
                    }}
                    className="focus-ring flex min-w-0 flex-1 items-center gap-3 rounded-md text-left"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{e.title}</p>
                      <p className="text-xs text-fg-muted">{relativeTime(e.createdAt)}</p>
                    </div>
                    <StatusPill tone={statusTone(e.status)}>{statusLabel(e.status)}</StatusPill>
                  </button>
                  <button
                    onClick={() => removeJob(e.jobId)}
                    aria-label={`Remove ${e.title}`}
                    className="focus-ring flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-fg-muted opacity-0 transition-opacity hover:bg-danger/10 hover:text-danger focus-visible:opacity-100 group-hover:opacity-100"
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex justify-end border-t border-border pt-4">
            <button
              onClick={clearHistory}
              className="focus-ring rounded-lg px-3 py-1.5 text-sm font-medium text-fg-muted transition-colors hover:text-danger"
            >
              Clear all
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
