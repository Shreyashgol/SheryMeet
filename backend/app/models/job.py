"""`jobs` table — the aggregate root of the pipeline.

A job tracks one uploaded audio file through the state machine. It owns the audio
metadata, current status/progress, error attribution, and the lifecycle
timestamps used to compute queue-wait and total pipeline latency.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Enum as SAEnum, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import JobStatus, StageName
from app.database.base import Base, TimestampMixin, UUIDMixin

# Named Postgres enum types (shared across tables where relevant).
job_status_enum = SAEnum(JobStatus, name="job_status", native_enum=True, validate_strings=True)
stage_name_enum = SAEnum(StageName, name="stage_name", native_enum=True, validate_strings=True)


class Job(UUIDMixin, TimestampMixin, Base):
    """A single meeting-processing job."""

    __tablename__ = "jobs"

    status: Mapped[JobStatus] = mapped_column(
        job_status_enum, nullable=False, default=JobStatus.QUEUED, index=True
    )
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # Audio metadata
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    audio_format: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Error attribution
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_stage: Mapped[StageName | None] = mapped_column(stage_name_enum, nullable=True)

    # Lifecycle timestamps (feed latency metrics)
    queued_at: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships (one-to-one for transcript/summary, one-to-many otherwise)
    transcript: Mapped["Transcript | None"] = relationship(  # noqa: F821
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    summary: Mapped["Summary | None"] = relationship(  # noqa: F821
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    action_items: Mapped[list["ActionItem"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan"
    )
    logs: Mapped[list["ProcessingLog"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Job id={self.id} status={self.status} progress={self.progress}>"
