import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { createJob } from "@/api/jobs";
import { ApiError } from "@/api/client";
import { Button, Card, cx } from "@/components/ui";

const ACCEPTED = [".wav", ".mp3"];
const MAX_BYTES = 200 * 1024 * 1024;

function isAccepted(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED.some((ext) => name.endsWith(ext));
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Upload screen: drag-and-drop (or pick) a meeting recording and start a job. */
export function UploadPage({
  onCreated,
}: {
  onCreated: (jobId: string, filename: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: createJob,
    onSuccess: (data, uploaded) => onCreated(data.job_id, uploaded.name),
  });

  const select = (f: File | null) => {
    setClientError(null);
    if (!f) return;
    if (!isAccepted(f)) {
      setClientError("Unsupported file type. Please upload a .wav or .mp3 file.");
      return;
    }
    if (f.size === 0) {
      setClientError("That file is empty.");
      return;
    }
    if (f.size > MAX_BYTES) {
      setClientError("File exceeds the 200 MB limit.");
      return;
    }
    setFile(f);
  };

  const serverError =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "Upload failed. Please try again."
        : null;

  return (
    <div className="mx-auto max-w-2xl animate-fade-in">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight">Meeting Intelligence</h1>
        <p className="mt-2 text-fg-muted">
          Upload a recording to get a structured summary and an accountable checklist.
        </p>
      </div>

      <Card>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            select(e.dataTransfer.files?.[0] ?? null);
          }}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
          className={cx(
            "focus-ring flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 text-center transition-colors",
            dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50",
          )}
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-2xl text-primary">
            ↑
          </div>
          <div>
            <p className="font-medium">
              {file ? file.name : "Drag & drop your audio here"}
            </p>
            <p className="mt-1 text-sm text-fg-muted">
              {file ? humanSize(file.size) : "or click to browse · WAV or MP3 · up to 200 MB"}
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".wav,.mp3,audio/wav,audio/mpeg"
            className="hidden"
            onChange={(e) => select(e.target.files?.[0] ?? null)}
          />
        </div>

        {(clientError || serverError) && (
          <p className="mt-4 rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
            {clientError ?? serverError}
          </p>
        )}

        <div className="mt-5 flex items-center justify-end gap-3">
          {file && (
            <Button variant="ghost" onClick={() => setFile(null)} disabled={mutation.isPending}>
              Clear
            </Button>
          )}
          <Button
            onClick={() => file && mutation.mutate(file)}
            disabled={!file || mutation.isPending}
          >
            {mutation.isPending ? "Uploading…" : "Process meeting"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
