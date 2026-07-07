"""Celery application: broker wiring, queue routing, and retry policy.

Each pipeline stage runs on its own dedicated queue so the four workers can be
scaled and tuned independently and never execute another stage's task. Job state
lives in Postgres (the source of truth); Celery is orchestration only.
"""

from __future__ import annotations

from celery import Celery, Task

from app.config.settings import get_settings
from app.core.enums import JobStatus, StageName
from app.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()

# Queue names — one per single-responsibility worker.
AUDIO_QUEUE = "audio.q"
TRANSCRIPT_QUEUE = "transcript.q"
SUMMARY_QUEUE = "summary.q"
CHECKLIST_QUEUE = "checklist.q"

celery_app = Celery(
    "meeting_intelligence",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=[
        "app.workers.audio_worker",
        "app.workers.transcript_worker",
        "app.workers.summary_worker",
        "app.workers.checklist_worker",
    ],
)

celery_app.conf.update(
    task_acks_late=True,                     # redeliver if a worker dies mid-task
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,            # fair dispatch for long-running tasks
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_time_limit=settings.celery_task_time_limit,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    task_routes={
        "app.workers.audio_worker.audio_stage": {"queue": AUDIO_QUEUE},
        "app.workers.transcript_worker.transcript_stage": {"queue": TRANSCRIPT_QUEUE},
        "app.workers.summary_worker.summary_stage": {"queue": SUMMARY_QUEUE},
        "app.workers.checklist_worker.checklist_stage": {"queue": CHECKLIST_QUEUE},
    },
)

# Inline (eager) execution: the whole chain runs synchronously in the caller.
# `task_eager_propagates=False` ensures a stage failure marks the job FAILED
# (via the worker error handling) instead of surfacing as an error in the HTTP
# request that dispatched it — the client still polls status as usual.
if settings.celery_task_always_eager:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False
    log.warning(
        "celery_eager_mode_enabled",
        note="pipeline runs inline in the API process; no broker/worker required",
    )


class PipelineTask(Task):
    """Base task that marks a job FAILED if a stage ultimately fails.

    Runs after retries are exhausted (transient failures) or immediately for
    permanent failures. Marking is idempotent, so it is safe alongside the
    stage's own inline failure handling.
    """

    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo) -> None:  # noqa: ANN001
        from app.database.session import session_scope
        from app.repositories.job_repo import JobRepository

        if not args:
            return
        try:
            import uuid

            job_id = uuid.UUID(str(args[0]))
        except (ValueError, TypeError):
            return
        stage = getattr(exc, "stage", None) or StageName.VALIDATION
        try:
            with session_scope() as session:
                repo = JobRepository(session)
                job = repo.get(job_id)
                if job and job.status != JobStatus.FAILED:
                    repo.mark_failed(job, stage=stage, message=str(exc))
        except Exception:  # noqa: BLE001 - never mask the original failure
            log.error("on_failure_mark_failed_error", job_id=str(job_id))


def check_broker() -> bool:
    """Return True if the Celery broker is reachable (used by the readiness probe)."""
    try:
        conn = celery_app.connection()
        conn.ensure_connection(max_retries=1, timeout=2)
        conn.release()
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("broker_healthcheck_failed", error=str(exc))
        return False
