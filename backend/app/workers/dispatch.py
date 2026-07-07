"""Celery implementation of the `PipelineDispatcher` port.

Builds the ordered stage chain (audio → transcript → summary → checklist),
passing only the job id between tasks. Broker connectivity errors are translated
into the domain `BrokerUnavailableError` so the API can return 503 without leaking
Celery/kombu exception types.

On broker-less deployments (e.g. Render's free tier, CELERY_TASK_ALWAYS_EAGER=true)
there is no worker or Redis to run a chain: a Celery chain would run only its first
stage eagerly and try to publish the rest to a non-existent broker, leaving the job
stuck at TRANSCRIBING. In that mode we instead run all four stages sequentially,
in-process, on a background thread so the POST returns immediately and the API can
report progress as each stage updates the job row.
"""

from __future__ import annotations

import threading
import uuid

from celery import chain
from kombu.exceptions import OperationalError as BrokerOperationalError

from app.config.settings import get_settings
from app.core.exceptions import BrokerUnavailableError
from app.core.logging import get_logger
from app.workers.audio_worker import audio_stage
from app.workers.checklist_worker import checklist_stage
from app.workers.summary_worker import summary_stage
from app.workers.transcript_worker import transcript_stage

log = get_logger(__name__)

# Ordered stages; each takes and returns the job-id string so it flows to the next.
_STAGES = (audio_stage, transcript_stage, summary_stage, checklist_stage)


class CeleryPipelineDispatcher:
    """Dispatch the processing pipeline — as a Celery chain, or inline when eager."""

    def dispatch(self, job_id: uuid.UUID) -> None:
        """Start the full pipeline for `job_id`.

        Raises:
            BrokerUnavailableError: if a broker-backed dispatch cannot reach the broker.
        """
        job_id_str = str(job_id)

        # Broker-less (free-tier) mode: run the stages inline on a background thread.
        if get_settings().celery_task_always_eager:
            threading.Thread(
                target=self._run_inline, args=(job_id_str,), daemon=True
            ).start()
            log.info("pipeline_dispatched_inline", job_id=job_id_str)
            return

        pipeline = chain(
            audio_stage.s(job_id_str),
            transcript_stage.s(),
            summary_stage.s(),
            checklist_stage.s(),
        )
        try:
            pipeline.apply_async()
        except (BrokerOperationalError, ConnectionError, OSError) as exc:
            # Only genuine broker/connection failures map to 503. In production,
            # apply_async never runs task code, so stage exceptions never surface
            # here — they are handled by the worker (and mark the job FAILED).
            log.error("pipeline_dispatch_failed", job_id=job_id_str, error=str(exc))
            raise BrokerUnavailableError("Could not enqueue processing pipeline") from exc
        log.info("pipeline_dispatched", job_id=job_id_str)

    @staticmethod
    def _run_inline(job_id_str: str) -> None:
        """Run every stage in order, in-process, passing the job id along.

        Each stage's own error handling (run_stage) marks the job FAILED and
        re-raises on a permanent error; we stop the pipeline there. This runs on a
        daemon thread, so exceptions are logged rather than propagated.
        """
        try:
            payload = job_id_str
            for stage in _STAGES:
                # .apply() runs the task eagerly in-process (no broker) and returns
                # an EagerResult; .get() yields the job id or re-raises a stage error.
                payload = stage.apply(args=[payload]).get()
        except Exception as exc:  # noqa: BLE001 - stage already marked the job FAILED
            log.error("inline_pipeline_failed", job_id=job_id_str, error=str(exc))
