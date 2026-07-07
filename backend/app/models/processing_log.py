"""`processing_logs` table — durable audit trail and metrics store (N:1 with job).

Every stage writes structured events here: stage start/finish, latencies, and
errors. `latency_ms` powers the observability read model (queue wait, ASR latency,
LLM latency, total pipeline latency) without a separate metrics table.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import LogLevel, StageName
from app.database.base import Base, UUIDMixin
from app.models.job import stage_name_enum

log_level_enum = SAEnum(LogLevel, name="log_level", native_enum=True, validate_strings=True)


class ProcessingLog(UUIDMixin, Base):
    """A single structured processing event for a job.

    Uses only `created_at` (append-only, immutable events) rather than the full
    Timestamp mixin.
    """

    __tablename__ = "processing_logs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stage: Mapped[StageName | None] = mapped_column(stage_name_enum, nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[LogLevel] = mapped_column(log_level_enum, nullable=False, default=LogLevel.INFO)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job: Mapped["Job"] = relationship(back_populates="logs")  # noqa: F821
