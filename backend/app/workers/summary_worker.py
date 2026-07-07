"""Summary Worker (Phase 8).

Single responsibility: generate the structured meeting summary from the cleaned
transcript via the LLM and persist it. It does not extract action items (that is
the Checklist Worker's job).

State transition owned by this stage: SUMMARIZING.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.enums import JobStatus, StageName
from app.core.exceptions import EmptyTranscriptError, TransientError
from app.providers.llm.factory import get_llm_provider
from app.repositories.summary_repo import SummaryRepository
from app.repositories.transcript_repo import TranscriptRepository
from app.services.summary_service import SummaryService
from app.workers.base import run_stage
from app.workers.celery_app import PipelineTask, celery_app

settings = get_settings()


@celery_app.task(
    name="app.workers.summary_worker.summary_stage",
    bind=True,
    base=PipelineTask,
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_backoff_max=int(settings.retry_backoff_max_seconds),
    retry_jitter=True,
    retry_kwargs={"max_retries": settings.retry_max_attempts},
    acks_late=True,
)
def summary_stage(self, job_id: str) -> str:  # noqa: ANN001
    """Generate and persist the structured summary for a job."""

    def work(session: Session, jid: uuid.UUID) -> None:
        transcript = TranscriptRepository(session).get_by_job(jid)
        text = (transcript.cleaned_text if transcript else None) or (
            transcript.raw_text if transcript else None
        )
        if not text or not text.strip():
            raise EmptyTranscriptError(
                "No transcript available to summarize", stage=StageName.SUMMARIZATION
            )

        service = SummaryService(
            get_llm_provider(),
            max_tokens=settings.llm_max_output_tokens,
            temperature=settings.llm_temperature,
        )
        summary, provider, model = service.summarize(text)
        SummaryRepository(session).create_from_schema(
            job_id=jid, data=summary, provider=provider, model=model
        )

    return run_stage(
        job_id, stage=StageName.SUMMARIZATION, entry_status=JobStatus.SUMMARIZING, work=work
    )
