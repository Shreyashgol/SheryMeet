"""Audio Worker (Phase 6).

Single responsibility: validate the uploaded audio, normalize it, and produce the
raw transcript via ASR. It does not clean, summarize, or extract actions.

State transitions owned by this stage: VALIDATING → TRANSCRIBING.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.enums import JobStatus, StageName
from app.core.exceptions import TransientError
from app.providers.asr.factory import get_asr_provider
from app.repositories.job_repo import JobRepository
from app.repositories.transcript_repo import TranscriptRepository
from app.services.audio_service import AudioService
from app.services.transcription_service import TranscriptionService
from app.storage.factory import get_storage
from app.workers.base import run_stage
from app.workers.celery_app import PipelineTask, celery_app

settings = get_settings()


@celery_app.task(
    name="app.workers.audio_worker.audio_stage",
    bind=True,
    base=PipelineTask,
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_backoff_max=int(settings.retry_backoff_max_seconds),
    retry_jitter=True,
    retry_kwargs={"max_retries": settings.retry_max_attempts},
    acks_late=True,
)
def audio_stage(self, job_id: str) -> str:  # noqa: ANN001
    """Validate + normalize audio and transcribe it to a raw transcript."""

    def work(session: Session, jid: uuid.UUID) -> None:
        jobs = JobRepository(session)
        job = jobs.get(jid)
        assert job is not None

        audio_service = AudioService(get_storage(), settings)
        info = audio_service.validate(job.storage_key, job.audio_format)
        jobs.set_duration(job, info.duration_seconds)
        session.commit()  # persist validation result before the long ASR step

        jobs.set_status(job, JobStatus.TRANSCRIBING)
        session.commit()

        normalized_path = audio_service.normalize(job.storage_key)
        transcription = TranscriptionService(get_asr_provider())
        result = transcription.transcribe(normalized_path, language=settings.asr_language)

        TranscriptRepository(session).create_raw(
            job_id=jid,
            raw_text=result.text,
            language=result.language,
            segments=result.segments_as_dicts() or None,
        )

    return run_stage(
        job_id, stage=StageName.VALIDATION, entry_status=JobStatus.VALIDATING, work=work
    )
