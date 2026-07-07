import { getJSON, postForm } from "./client";

// ── Types mirroring the backend DTOs (app/schemas) ─────────────────────────────

export type JobStatus =
  | "QUEUED"
  | "VALIDATING"
  | "UPLOADING"
  | "TRANSCRIBING"
  | "CLEANING"
  | "SUMMARIZING"
  | "EXTRACTING_ACTIONS"
  | "COMPLETED"
  | "FAILED";

export const TERMINAL_STATUSES: JobStatus[] = ["COMPLETED", "FAILED"];

export interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  timestamps: {
    created_at: string;
    queued_at: string | null;
    started_at: string | null;
    completed_at: string | null;
  };
  error_stage: string | null;
  error_message: string | null;
}

export type Priority = "High" | "Medium" | "Low";

export interface ActionItem {
  id: string;
  owner: string;
  task: string;
  deadline: string;
  priority: Priority;
  status: string;
}

export interface Summary {
  meeting_title: string;
  summary: string;
  agenda: string[];
  key_decisions: string[];
  risks: string[];
  blockers: string[];
  next_steps: string[];
}

export interface ResultMetadata {
  audio_format: string;
  duration_seconds: number | null;
  language: string | null;
  llm_provider: string;
  llm_model: string;
  latencies_ms: Record<string, number>;
  total_pipeline_ms: number | null;
}

export interface JobResult {
  job_id: string;
  summary: Summary;
  checklist: ActionItem[];
  metadata: ResultMetadata;
}

// ── API calls ──────────────────────────────────────────────────────────────────

export function createJob(file: File): Promise<JobCreateResponse> {
  const form = new FormData();
  form.append("file", file);
  return postForm<JobCreateResponse>("/jobs", form);
}

export function getJob(jobId: string): Promise<JobStatusResponse> {
  return getJSON<JobStatusResponse>(`/jobs/${jobId}`);
}

export function getJobResult(jobId: string): Promise<JobResult> {
  return getJSON<JobResult>(`/jobs/${jobId}/result`);
}
