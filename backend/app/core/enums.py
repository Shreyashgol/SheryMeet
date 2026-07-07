"""Domain enumerations shared across the application.

Centralising these prevents "stringly-typed" bugs and gives a single place to
evolve the state machine. Values are stored verbatim in Postgres enum types.
"""

from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    """Lifecycle states of a processing job (the pipeline state machine)."""

    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    UPLOADING = "UPLOADING"
    TRANSCRIBING = "TRANSCRIBING"
    CLEANING = "CLEANING"
    SUMMARIZING = "SUMMARIZING"
    EXTRACTING_ACTIONS = "EXTRACTING_ACTIONS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        """Whether no further transitions are expected from this state."""
        return self in {JobStatus.COMPLETED, JobStatus.FAILED}


class StageName(str, Enum):
    """Pipeline stage identifiers, used for logs, metrics and error attribution."""

    VALIDATION = "VALIDATION"
    TRANSCRIPTION = "TRANSCRIPTION"
    CLEANING = "CLEANING"
    SUMMARIZATION = "SUMMARIZATION"
    CHECKLIST = "CHECKLIST"


class Priority(str, Enum):
    """Action-item priority levels."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ActionItemStatus(str, Enum):
    """Action-item completion status."""

    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class LogLevel(str, Enum):
    """Severity levels for persisted processing logs."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Progress checkpoints (percent) associated with each job status. Kept here so the
# API's reported progress and the workers' updates cannot drift apart.
STATUS_PROGRESS: dict[JobStatus, int] = {
    JobStatus.QUEUED: 0,
    JobStatus.VALIDATING: 5,
    JobStatus.UPLOADING: 10,
    JobStatus.TRANSCRIBING: 30,
    JobStatus.CLEANING: 55,
    JobStatus.SUMMARIZING: 75,
    JobStatus.EXTRACTING_ACTIONS: 90,
    JobStatus.COMPLETED: 100,
    JobStatus.FAILED: 100,
}
