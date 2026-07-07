"""Domain exception hierarchy.

The hierarchy encodes retry semantics so orchestration code can decide, without
inspecting error strings, whether a failure is worth retrying:

    PipelineError
    ├── TransientError   → safe to retry (network blips, timeouts, 5xx, rate limits)
    └── PermanentError   → do NOT retry (bad input, empty transcript, schema violation)

Every worker maps low-level SDK exceptions onto this hierarchy at the boundary,
keeping business logic free of vendor-specific error types.
"""

from __future__ import annotations

from app.core.enums import StageName


class PipelineError(Exception):
    """Base class for all domain errors raised inside the pipeline."""

    def __init__(self, message: str, *, stage: StageName | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage


class TransientError(PipelineError):
    """A recoverable failure; the operation may succeed if retried."""


class PermanentError(PipelineError):
    """An unrecoverable failure; retrying will not help."""


# ── Transient specialisations ────────────────────────────────────────────────
class ASRTimeoutError(TransientError):
    """Speech recognition exceeded its time budget."""


class LLMTimeoutError(TransientError):
    """An LLM call exceeded its time budget."""


class LLMRateLimitError(TransientError):
    """An LLM provider signalled rate limiting (HTTP 429)."""


class LLMServerError(TransientError):
    """An LLM provider returned a 5xx server error."""


class BrokerUnavailableError(TransientError):
    """The message broker (Redis) could not be reached."""


class DatabaseUnavailableError(TransientError):
    """The database could not be reached (transient connectivity issue)."""


# ── Permanent specialisations ────────────────────────────────────────────────
class UnsupportedAudioError(PermanentError):
    """The uploaded file is not a supported audio format."""


class InvalidAudioError(PermanentError):
    """The audio is corrupt, empty, or otherwise undecodable."""


class EmptyTranscriptError(PermanentError):
    """ASR produced no usable text (e.g. silent recording)."""


class LLMOutputValidationError(PermanentError):
    """The LLM response could not be parsed/validated against the schema."""


class JobNotFoundError(PermanentError):
    """A requested job does not exist."""


class ResultNotReadyError(PermanentError):
    """A job's result was requested before the job reached COMPLETED."""
