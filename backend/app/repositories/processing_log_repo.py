"""Repository for `ProcessingLog` events (audit trail + metrics store)."""

from __future__ import annotations

import uuid
from typing import Sequence

from app.core.enums import LogLevel, StageName
from app.models.processing_log import ProcessingLog
from app.repositories.base import BaseRepository


class ProcessingLogRepository(BaseRepository[ProcessingLog]):
    """Append-only access to processing events."""

    model = ProcessingLog

    def record(
        self,
        *,
        job_id: uuid.UUID,
        event: str,
        stage: StageName | None = None,
        level: LogLevel = LogLevel.INFO,
        message: str | None = None,
        latency_ms: int | None = None,
        meta: dict | None = None,
    ) -> ProcessingLog:
        """Append a structured processing event for a job."""
        entry = ProcessingLog(
            job_id=job_id,
            event=event,
            stage=stage,
            level=level,
            message=message,
            latency_ms=latency_ms,
            meta=meta,
        )
        return self.add(entry)

    def list_by_job(self, job_id: uuid.UUID) -> Sequence[ProcessingLog]:
        """Return all events for a job in chronological order."""
        return (
            self.session.query(ProcessingLog)
            .filter(ProcessingLog.job_id == job_id)
            .order_by(ProcessingLog.created_at.asc())
            .all()
        )

    def stage_latencies(self, job_id: uuid.UUID) -> dict[str, int]:
        """Return a map of stage → latency_ms for completed stages.

        Powers the observability read model exposed in the result endpoint.
        """
        rows = (
            self.session.query(ProcessingLog.stage, ProcessingLog.latency_ms)
            .filter(
                ProcessingLog.job_id == job_id,
                ProcessingLog.latency_ms.isnot(None),
                ProcessingLog.stage.isnot(None),
            )
            .all()
        )
        return {stage.value: latency for stage, latency in rows if stage is not None}
