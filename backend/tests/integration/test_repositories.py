"""Integration tests for repositories against a real database."""

from __future__ import annotations

from app.core.enums import JobStatus, StageName
from app.repositories.job_repo import JobRepository
from app.repositories.processing_log_repo import ProcessingLogRepository
from app.repositories.transcript_repo import TranscriptRepository
from tests.conftest import requires_db


@requires_db
def test_job_lifecycle_transitions(db_session) -> None:  # noqa: ANN001
    jobs = JobRepository(db_session)
    job = jobs.create(
        original_filename="m.wav", storage_key="k.wav", audio_format="wav", size_bytes=10
    )
    assert job.status == JobStatus.QUEUED
    assert job.queued_at is not None

    jobs.set_status(job, JobStatus.VALIDATING)
    assert job.started_at is not None
    assert job.progress == 5

    jobs.mark_failed(job, stage=StageName.TRANSCRIPTION, message="boom")
    assert job.status == JobStatus.FAILED
    assert job.error_stage == StageName.TRANSCRIPTION
    assert job.completed_at is not None
    db_session.rollback()


@requires_db
def test_transcript_roundtrip(db_session) -> None:  # noqa: ANN001
    jobs = JobRepository(db_session)
    transcripts = TranscriptRepository(db_session)
    job = jobs.create(original_filename="m.wav", storage_key="k", audio_format="wav", size_bytes=1)

    t = transcripts.create_raw(job_id=job.id, raw_text="hello world", language="en", segments=None)
    assert t.word_count == 2
    transcripts.set_cleaned(t, "Hello world.")
    assert transcripts.get_by_job(job.id).cleaned_text == "Hello world."
    db_session.rollback()


@requires_db
def test_processing_log_latencies(db_session) -> None:  # noqa: ANN001
    jobs = JobRepository(db_session)
    logs = ProcessingLogRepository(db_session)
    job = jobs.create(original_filename="m.wav", storage_key="k", audio_format="wav", size_bytes=1)

    logs.record(job_id=job.id, stage=StageName.TRANSCRIPTION, event="done", latency_ms=120)
    logs.record(job_id=job.id, stage=StageName.SUMMARIZATION, event="done", latency_ms=80)
    latencies = logs.stage_latencies(job.id)
    assert latencies["TRANSCRIPTION"] == 120
    assert latencies["SUMMARIZATION"] == 80
    db_session.rollback()
