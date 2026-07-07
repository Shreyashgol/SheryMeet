"""Shared stage-execution scaffolding for pipeline workers.

`run_stage` centralises the cross-cutting concerns every worker shares — job-state
transition, structured logging with the job id bound, per-stage latency
measurement, and the transient-vs-permanent error contract — so each worker file
contains only its own single responsibility (the `work` callable).

Error contract:
- TransientError → re-raised so Celery's autoretry reschedules the task.
- Any other exception → job marked FAILED and re-raised, which aborts the chain
  (downstream stages never run).
"""

from __future__ import annotations

import uuid
from typing import Callable

from sqlalchemy.orm import Session

from app.core.enums import JobStatus, LogLevel, StageName
from app.core.exceptions import TransientError
from app.core.logging import bind_job_context, clear_job_context, get_logger
from app.core.metrics import measure
from app.database.session import session_scope
from app.repositories.job_repo import JobRepository
from app.repositories.processing_log_repo import ProcessingLogRepository

log = get_logger(__name__)

# A unit of stage work: receives an open session and the job id, does its job,
# and writes its output rows. Status/latency/error handling is done by run_stage.
StageWork = Callable[[Session, uuid.UUID], None]


def run_stage(
    job_id_str: str,
    *,
    stage: StageName,
    entry_status: JobStatus,
    work: StageWork,
) -> str:
    """Execute one pipeline stage with shared state/logging/error handling.

    Returns the job id string so it flows to the next task in the Celery chain.
    """
    job_id = uuid.UUID(job_id_str)
    bind_job_context(job_id_str, stage=stage.value)
    try:
        # 1) Transition to the entry status and record the start (committed so the
        #    API reflects progress while long-running work proceeds).
        with session_scope() as session:
            jobs = JobRepository(session)
            job = jobs.get(job_id)
            if job is None:
                log.error("stage_job_missing")
                raise RuntimeError(f"Job {job_id} not found")
            if job.status == JobStatus.FAILED:
                # A prior stage failed; do not proceed.
                raise RuntimeError("Job already failed; aborting stage")
            jobs.set_status(job, entry_status)
            ProcessingLogRepository(session).record(
                job_id=job_id, stage=stage, event=f"{stage.value.lower()}_started"
            )

        # 2) Do the actual work, measuring latency.
        with measure() as sw:
            with session_scope() as session:
                work(session, job_id)

        # 3) Record success + latency.
        with session_scope() as session:
            ProcessingLogRepository(session).record(
                job_id=job_id,
                stage=stage,
                event=f"{stage.value.lower()}_finished",
                latency_ms=sw.elapsed_ms,
            )
        log.info("stage_complete", latency_ms=sw.elapsed_ms)
        return job_id_str

    except TransientError as exc:
        # Let Celery autoretry handle it; do not mark the job failed yet.
        log.warning("stage_transient_error", error=exc.message)
        _record_error(job_id, stage, str(exc), LogLevel.WARNING)
        raise
    except Exception as exc:  # noqa: BLE001 - permanent/unexpected → fail fast
        log.error("stage_failed", error=str(exc))
        _fail_job(job_id, stage, str(exc))
        raise
    finally:
        clear_job_context()


def _fail_job(job_id: uuid.UUID, stage: StageName, message: str) -> None:
    """Mark the job FAILED and record an error log."""
    try:
        with session_scope() as session:
            repo = JobRepository(session)
            job = repo.get(job_id)
            if job and job.status != JobStatus.FAILED:
                repo.mark_failed(job, stage=stage, message=message)
            ProcessingLogRepository(session).record(
                job_id=job_id, stage=stage, event="stage_failed", level=LogLevel.ERROR,
                message=message,
            )
    except Exception:  # noqa: BLE001 - never mask the original error
        log.error("fail_job_persist_error", job_id=str(job_id))


def _record_error(job_id: uuid.UUID, stage: StageName, message: str, level: LogLevel) -> None:
    """Append an error/warning processing log without changing job status."""
    try:
        with session_scope() as session:
            ProcessingLogRepository(session).record(
                job_id=job_id, stage=stage, event="stage_error", level=level, message=message
            )
    except Exception:  # noqa: BLE001
        log.error("record_error_persist_error", job_id=str(job_id))
