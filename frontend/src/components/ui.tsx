import type { ButtonHTMLAttributes, ReactNode } from "react";

import type { Priority } from "@/api/jobs";
import type { Tone } from "@/lib/status";

/** Simple className joiner. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("card p-5", className)}>{children}</div>;
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
}

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  const base =
    "focus-ring inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none";
  const styles =
    variant === "primary"
      ? "bg-primary text-primary-fg hover:opacity-90"
      : "border border-border bg-card text-fg hover:bg-muted";
  return <button className={cx(base, styles, className)} {...props} />;
}

const TONE_CLASSES: Record<Tone, string> = {
  info: "bg-primary/10 text-primary",
  progress: "bg-warning/15 text-warning",
  success: "bg-success/15 text-success",
  danger: "bg-danger/15 text-danger",
};

export function StatusPill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
        TONE_CLASSES[tone],
      )}
    >
      {tone === "progress" && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-warning" aria-hidden />
      )}
      {children}
    </span>
  );
}

const PRIORITY_CLASSES: Record<Priority, string> = {
  High: "bg-danger/15 text-danger",
  Medium: "bg-warning/15 text-warning",
  Low: "bg-success/15 text-success",
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span
      className={cx(
        "inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold",
        PRIORITY_CLASSES[priority] ?? "bg-muted text-fg-muted",
      )}
    >
      {priority}
    </span>
  );
}

export function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-muted"
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

export function EmptyList({ children }: { children: ReactNode }) {
  return <p className="text-sm text-fg-muted">{children}</p>;
}
