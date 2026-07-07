import type { JobStatus } from "@/api/jobs";

/** Ordered pipeline stages shown in the progress stepper. */
export const PIPELINE_STEPS: { key: JobStatus; label: string }[] = [
  { key: "QUEUED", label: "Queued" },
  { key: "VALIDATING", label: "Validating" },
  { key: "TRANSCRIBING", label: "Transcribing" },
  { key: "CLEANING", label: "Cleaning" },
  { key: "SUMMARIZING", label: "Summarizing" },
  { key: "EXTRACTING_ACTIONS", label: "Extracting actions" },
  { key: "COMPLETED", label: "Completed" },
];

const STATUS_ORDER: JobStatus[] = [
  "QUEUED",
  "VALIDATING",
  "UPLOADING",
  "TRANSCRIBING",
  "CLEANING",
  "SUMMARIZING",
  "EXTRACTING_ACTIONS",
  "COMPLETED",
];

/** Index of a status in the linear pipeline (FAILED maps to -1). */
export function statusIndex(status: JobStatus): number {
  return STATUS_ORDER.indexOf(status);
}

export function statusLabel(status: JobStatus): string {
  const found = PIPELINE_STEPS.find((s) => s.key === status);
  if (found) return found.label;
  if (status === "FAILED") return "Failed";
  if (status === "UPLOADING") return "Uploading";
  return status;
}

export type Tone = "info" | "progress" | "success" | "danger";

export function statusTone(status: JobStatus): Tone {
  if (status === "COMPLETED") return "success";
  if (status === "FAILED") return "danger";
  if (status === "QUEUED") return "info";
  return "progress";
}
