"""Transcript Worker (Phase 7).

Single responsibility: normalize the raw transcript (filler removal, spacing,
punctuation/boundary repair) while preserving speaker labels. It does not
transcribe, summarize, or extract actions.

State transition owned by this stage: CLEANING.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.enums import JobStatus, StageName
from app.core.exceptions import EmptyTranscriptError, TransientError
from app.repositories.transcript_repo import TranscriptRepository
from app.services.cleaning_service import CleaningService
from app.workers.base import run_stage
from app.workers.celery_app import PipelineTask, celery_app

settings = get_settings()


@celery_app.task(
    name="app.workers.transcript_worker.transcript_stage",
    bind=True,
    base=PipelineTask,
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_backoff_max=int(settings.retry_backoff_max_seconds),
    retry_jitter=True,
    retry_kwargs={"max_retries": settings.retry_max_attempts},
    acks_late=True,
)
def transcript_stage(self, job_id: str) -> str:  # noqa: ANN001
    """Clean and normalize the raw transcript for a job."""

    def work(session: Session, jid: uuid.UUID) -> None:
        transcripts = TranscriptRepository(session)
        transcript = transcripts.get_by_job(jid)
        if transcript is None or not transcript.raw_text.strip():
            raise EmptyTranscriptError(
                "No raw transcript to clean", stage=StageName.CLEANING
            )
        cleaned = CleaningService().clean(transcript.raw_text)
        if not cleaned.strip():
            raise EmptyTranscriptError(
                "Transcript was empty after cleaning", stage=StageName.CLEANING
            )
        transcripts.set_cleaned(transcript, cleaned)

    return run_stage(
        job_id, stage=StageName.CLEANING, entry_status=JobStatus.CLEANING, work=work
    )
