"""Celery implementation of the `PipelineDispatcher` port.

Builds the ordered stage chain (audio → transcript → summary → checklist),
passing only the job id between tasks. Broker connectivity errors are translated
into the domain `BrokerUnavailableError` so the API can return 503 without leaking
Celery/kombu exception types.
"""

from __future__ import annotations

import uuid

from celery import chain
from kombu.exceptions import OperationalError as BrokerOperationalError

from app.core.exceptions import BrokerUnavailableError
from app.core.logging import get_logger
from app.workers.audio_worker import audio_stage
from app.workers.checklist_worker import checklist_stage
from app.workers.summary_worker import summary_stage
from app.workers.transcript_worker import transcript_stage

log = get_logger(__name__)


class CeleryPipelineDispatcher:
    """Dispatch the processing pipeline as a Celery chain."""

    def dispatch(self, job_id: uuid.UUID) -> None:
        """Enqueue the full pipeline for `job_id`.

        Raises:
            BrokerUnavailableError: if the message broker cannot be reached.
        """
        job_id_str = str(job_id)
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
