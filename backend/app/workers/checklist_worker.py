"""Checklist Worker (Phase 9).

Single responsibility: extract the accountable action items from the transcript
via the LLM, persist them, and mark the job COMPLETED. It does not summarize.

State transitions owned by this stage: EXTRACTING_ACTIONS → COMPLETED.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.enums import JobStatus, StageName
from app.core.exceptions import EmptyTranscriptError, PermanentError, TransientError
from app.providers.llm.factory import get_llm_provider
from app.repositories.action_item_repo import ActionItemRepository
from app.repositories.job_repo import JobRepository
from app.repositories.summary_repo import SummaryRepository
from app.repositories.transcript_repo import TranscriptRepository
from app.services.checklist_service import ChecklistService
from app.workers.base import run_stage
from app.workers.celery_app import PipelineTask, celery_app

settings = get_settings()


@celery_app.task(
    name="app.workers.checklist_worker.checklist_stage",
    bind=True,
    base=PipelineTask,
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_backoff_max=int(settings.retry_backoff_max_seconds),
    retry_jitter=True,
    retry_kwargs={"max_retries": settings.retry_max_attempts},
    acks_late=True,
)
def checklist_stage(self, job_id: str) -> str:  # noqa: ANN001
    """Extract and persist action items, then complete the job."""

    def work(session: Session, jid: uuid.UUID) -> None:
        summary = SummaryRepository(session).get_by_job(jid)
        if summary is None:
            raise PermanentError(
                "Cannot extract checklist before a summary exists", stage=StageName.CHECKLIST
            )

        transcript = TranscriptRepository(session).get_by_job(jid)
        text = (transcript.cleaned_text if transcript else None) or (
            transcript.raw_text if transcript else None
        )
        if not text or not text.strip():
            raise EmptyTranscriptError(
                "No transcript available for checklist extraction", stage=StageName.CHECKLIST
            )

        service = ChecklistService(
            get_llm_provider(),
            max_tokens=settings.llm_max_output_tokens,
            temperature=settings.llm_temperature,
        )
        items = service.extract(text)
        ActionItemRepository(session).bulk_create(
            job_id=jid, summary_id=summary.id, items=items
        )

        # Terminal transition: the pipeline is complete.
        jobs = JobRepository(session)
        job = jobs.get(jid)
        assert job is not None
        jobs.set_status(job, JobStatus.COMPLETED)

    return run_stage(
        job_id,
        stage=StageName.CHECKLIST,
        entry_status=JobStatus.EXTRACTING_ACTIONS,
        work=work,
    )
