import { Modal } from "@/components/Modal";

const STEPS: { title: string; body: string }[] = [
  {
    title: "Upload a recording",
    body: "Drag & drop or browse to a meeting audio file — WAV or MP3, up to 200 MB.",
  },
  {
    title: "Let it process",
    body: "The pipeline transcribes, cleans, summarizes, and extracts action items. Watch the live progress stepper; a first run after idle can take a little longer while the server wakes up.",
  },
  {
    title: "Review the results",
    body: "You get a structured summary — agenda, key decisions, risks, blockers, next steps — plus an accountable checklist of who owns what, by when.",
  },
  {
    title: "Come back anytime",
    body: "Every meeting you process is saved to History on this device. Reopen a past result in one click. History is private to this browser.",
  },
];

/** Onboarding guide explaining the upload → process → review → history flow. */
export function HowToUseModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Modal open={open} onClose={onClose} title="How to use SheryMeet" wide>
      <ol className="space-y-4">
        {STEPS.map((step, i) => (
          <li key={i} className="flex gap-4">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
              {i + 1}
            </span>
            <div>
              <p className="font-medium">{step.title}</p>
              <p className="mt-0.5 text-sm text-fg-muted">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
      <div className="mt-5 rounded-lg bg-muted px-4 py-3 text-sm text-fg-muted">
        <span className="font-medium text-fg">Tip:</span> clear audio with distinct
        speakers produces the best summaries and action items.
      </div>
    </Modal>
  );
}
