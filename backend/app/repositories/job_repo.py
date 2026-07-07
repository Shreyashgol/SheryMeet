"""Repository for the `Job` aggregate root."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.enums import STATUS_PROGRESS, JobStatus, StageName
from app.models.job import Job
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Data access and state transitions for jobs."""

    model = Job

    def create(
        self,
        *,
        original_filename: str,
        storage_key: str,
        audio_format: str,
        size_bytes: int,
    ) -> Job:
        """Create a new job in the QUEUED state with queue timestamp set."""
        job = Job(
            status=JobStatus.QUEUED,
            progress=STATUS_PROGRESS[JobStatus.QUEUED],
            original_filename=original_filename,
            storage_key=storage_key,
            audio_format=audio_format,
            size_bytes=size_bytes,
            queued_at=datetime.now(timezone.utc),
        )
        return self.add(job)

    def set_status(self, job: Job, status: JobStatus) -> Job:
        """Transition a job to a new status and update its derived progress.

        Also stamps `started_at` on first active transition and `completed_at`
        when reaching a terminal state, so latency metrics can be derived.
        """
        now = datetime.now(timezone.utc)
        job.status = status
        job.progress = STATUS_PROGRESS[status]
        if status == JobStatus.VALIDATING and job.started_at is None:
            job.started_at = now
        if status.is_terminal:
            job.completed_at = now
        self.session.flush()
        return job

    def mark_failed(self, job: Job, *, stage: StageName, message: str) -> Job:
        """Mark a job as FAILED with error attribution."""
        job.error_stage = stage
        job.error_message = message[:2000]
        return self.set_status(job, JobStatus.FAILED)

    def set_duration(self, job: Job, duration_seconds: float) -> Job:
        """Persist the decoded audio duration (used for metrics)."""
        job.duration_seconds = round(duration_seconds, 2)
        self.session.flush()
        return job

    def get_or_raise(self, job_id: uuid.UUID) -> Job | None:
        """Return a job by id (None if absent); raising is left to the service."""
        return self.get(job_id)
