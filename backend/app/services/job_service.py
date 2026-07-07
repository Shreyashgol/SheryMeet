"""Job application service (Phases 3 & 10).

Orchestrates the API-facing use cases — create a job from an upload, report its
status, and assemble its result — while delegating persistence to repositories,
file storage to the storage port, and pipeline scheduling to the injected
dispatcher. Contains no HTTP or Celery details.
"""

from __future__ import annotations

import uuid
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.enums import JobStatus
from app.core.exceptions import JobNotFoundError, ResultNotReadyError, UnsupportedAudioError
from app.core.logging import get_logger
from app.repositories.action_item_repo import ActionItemRepository
from app.repositories.job_repo import JobRepository
from app.repositories.processing_log_repo import ProcessingLogRepository
from app.repositories.summary_repo import SummaryRepository
from app.repositories.transcript_repo import TranscriptRepository
from app.schemas.job import JobCreateResponse, JobStatusResponse, JobTimestamps, ResultMetadata
from app.schemas.result import ActionItemOut, JobResultResponse, SummaryOut
from app.services.ports import PipelineDispatcher
from app.storage.base import ObjectStorage
from app.utils.audio import ensure_supported

log = get_logger(__name__)


class JobService:
    """Use cases for creating and querying meeting-processing jobs."""

    def __init__(
        self,
        session: Session,
        storage: ObjectStorage,
        dispatcher: PipelineDispatcher,
        settings: Settings,
    ) -> None:
        self._session = session
        self._storage = storage
        self._dispatcher = dispatcher
        self._settings = settings
        self._jobs = JobRepository(session)
        self._transcripts = TranscriptRepository(session)
        self._summaries = SummaryRepository(session)
        self._action_items = ActionItemRepository(session)
        self._logs = ProcessingLogRepository(session)

    # ── Command: create ────────────────────────────────────────────────────────
    def create_job(self, *, filename: str, stream: BinaryIO, size_bytes: int) -> JobCreateResponse:
        """Validate the upload, persist the file and job row, and dispatch the pipeline.

        Only syntactic validation (extension + size) happens here; deep audio
        validation is performed by the audio worker.
        """
        if size_bytes <= 0:
            raise UnsupportedAudioError("Uploaded file is empty")
        if size_bytes > self._settings.max_upload_bytes:
            from app.core.exceptions import PermanentError

            raise PermanentError(
                f"File exceeds maximum size of {self._settings.max_upload_bytes} bytes"
            )

        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        audio_format = ensure_supported(extension, self._settings.allowed_audio_formats)

        storage_key = f"{uuid.uuid4()}.{audio_format}"
        self._storage.save(storage_key, stream)

        job = self._jobs.create(
            original_filename=filename,
            storage_key=storage_key,
            audio_format=audio_format,
            size_bytes=size_bytes,
        )
        self._logs.record(job_id=job.id, event="job_created", meta={"filename": filename})
        # Commit so the row is durable and visible to the worker before dispatch.
        self._session.commit()

        self._dispatcher.dispatch(job.id)
        log.info("job_created", job_id=str(job.id), size_bytes=size_bytes)
        return JobCreateResponse(job_id=job.id, status=job.status)

    # ── Query: status ───────────────────────────────────────────────────────────
    def get_status(self, job_id: uuid.UUID) -> JobStatusResponse:
        """Return the current status/progress/timestamps for a job."""
        job = self._require_job(job_id)
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            timestamps=JobTimestamps(
                created_at=job.created_at,
                queued_at=job.queued_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            ),
            error_stage=job.error_stage,
            error_message=job.error_message,
        )

    # ── Query: result ────────────────────────────────────────────────────────────
    def get_result(self, job_id: uuid.UUID) -> JobResultResponse:
        """Assemble the full result (summary + checklist + metadata) for a job.

        Raises:
            ResultNotReadyError: if the job has not reached COMPLETED.
        """
        job = self._require_job(job_id)
        if job.status != JobStatus.COMPLETED:
            raise ResultNotReadyError(f"Job is not complete (status={job.status.value})")

        summary = self._summaries.get_by_job(job_id)
        transcript = self._transcripts.get_by_job(job_id)
        items = self._action_items.list_by_job(job_id)
        latencies = self._logs.stage_latencies(job_id)

        total_ms: int | None = None
        if job.started_at and job.completed_at:
            total_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)

        assert summary is not None  # guaranteed for COMPLETED jobs
        return JobResultResponse(
            job_id=job.id,
            summary=SummaryOut(
                meeting_title=summary.meeting_title,
                summary=summary.summary,
                agenda=summary.agenda,
                key_decisions=summary.key_decisions,
                risks=summary.risks,
                blockers=summary.blockers,
                next_steps=summary.next_steps,
            ),
            checklist=[
                ActionItemOut(
                    id=item.id,
                    owner=item.owner,
                    task=item.task,
                    deadline=item.deadline,
                    priority=item.priority,
                    status=item.status,
                )
                for item in items
            ],
            metadata=ResultMetadata(
                audio_format=job.audio_format,
                duration_seconds=float(job.duration_seconds) if job.duration_seconds else None,
                language=transcript.language if transcript else None,
                llm_provider=summary.provider,
                llm_model=summary.model,
                latencies_ms=latencies,
                total_pipeline_ms=total_ms,
            ),
        )

    def _require_job(self, job_id: uuid.UUID):
        """Fetch a job or raise `JobNotFoundError`."""
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job
