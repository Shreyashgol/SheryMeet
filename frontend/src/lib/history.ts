/**
 * Client-side job history, persisted per browser in localStorage.
 *
 * The backend has no "list my jobs" endpoint (and no auth), so history lives on
 * the device: every job the user starts is recorded here, and past results are
 * reopened through the existing /jobs/{id} endpoints. A tiny pub/sub backs a
 * `useHistory()` hook via useSyncExternalStore, and a `storage` listener keeps
 * multiple tabs in sync.
 */
import { useSyncExternalStore } from "react";

import type { JobStatus } from "@/api/jobs";

const KEY = "sherymeet.history.v1";
const MAX_ENTRIES = 50;

export interface HistoryEntry {
  jobId: string;
  title: string;
  createdAt: string; // ISO timestamp
  status: JobStatus;
}

type Listener = () => void;
const listeners = new Set<Listener>();

// Cached snapshot so useSyncExternalStore gets a stable reference between
// renders (returning a fresh array each call would loop forever).
let cache: HistoryEntry[] | null = null;

function read(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

function ensure(): HistoryEntry[] {
  if (cache === null) cache = read();
  return cache;
}

function commit(entries: HistoryEntry[]): void {
  cache = entries;
  try {
    localStorage.setItem(KEY, JSON.stringify(entries));
  } catch {
    /* quota / private mode — history is best-effort */
  }
  listeners.forEach((l) => l());
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key === KEY) {
      cache = read();
      listeners.forEach((l) => l());
    }
  });
}

/** Insert (or move to top) a freshly created job. */
export function recordJob(jobId: string, title: string): void {
  const rest = ensure().filter((e) => e.jobId !== jobId);
  const entry: HistoryEntry = {
    jobId,
    title: title.trim() || "Untitled meeting",
    createdAt: new Date().toISOString(),
    status: "QUEUED",
  };
  commit([entry, ...rest].slice(0, MAX_ENTRIES));
}

/** Patch an existing entry (no-op if it isn't tracked on this device). */
export function updateJob(
  jobId: string,
  patch: Partial<Pick<HistoryEntry, "title" | "status">>,
): void {
  const entries = ensure();
  const idx = entries.findIndex((e) => e.jobId === jobId);
  if (idx === -1) return;
  const next = [...entries];
  next[idx] = { ...next[idx], ...patch };
  commit(next);
}

export function removeJob(jobId: string): void {
  commit(ensure().filter((e) => e.jobId !== jobId));
}

export function clearHistory(): void {
  commit([]);
}

function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Reactive view of the history list. */
export function useHistory(): HistoryEntry[] {
  return useSyncExternalStore(subscribe, ensure, () => []);
}
