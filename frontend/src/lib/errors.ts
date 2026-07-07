/**
 * Turns a raw backend/network error string into a user-facing message.
 *
 * The backend stores free-text `error_message` on failed jobs and returns error
 * envelopes on requests; this maps the common, actionable cases (chiefly AI
 * provider rate limits on the free tier) to clear guidance instead of leaking
 * vendor error text to the user.
 */
export interface FriendlyError {
  title: string;
  message: string;
  /** True when the failure is an AI-provider rate limit (HTTP 429 / quota). */
  isRateLimit: boolean;
  /** The original text, kept for an optional "details" disclosure. */
  raw: string;
}

const RATE_LIMIT_RE = /rate.?limit|\b429\b|too many requests|quota|max retries/i;
const TIMEOUT_RE = /timed? out|timeout/i;

export function classifyError(raw?: string | null): FriendlyError {
  const text = (raw ?? "").trim();

  if (RATE_LIMIT_RE.test(text)) {
    return {
      title: "AI service is busy right now",
      message:
        "The free-tier AI service hit its rate limit. Please wait about 30 seconds, then try again.",
      isRateLimit: true,
      raw: text,
    };
  }

  if (TIMEOUT_RE.test(text)) {
    return {
      title: "The request timed out",
      message:
        "Processing took too long and timed out. This can happen with long recordings on the free tier — try again, or use a shorter clip.",
      isRateLimit: false,
      raw: text,
    };
  }

  return {
    title: "Processing failed",
    message: text || "Something went wrong while processing this meeting. Please try again.",
    isRateLimit: false,
    raw: text,
  };
}
