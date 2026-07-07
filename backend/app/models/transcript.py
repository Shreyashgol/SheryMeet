"""`transcripts` table — raw and cleaned ASR output (1:1 with a job).

`segments` (JSONB) stores timestamped, optionally speaker-labelled segments. It is
nullable and forward-compatible with speaker diarization without a schema change.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import StageName
from app.database.base import Base, TimestampMixin, UUIDMixin
from app.models.job import stage_name_enum


class Transcript(UUIDMixin, TimestampMixin, Base):
    """The transcription produced for a job."""

    __tablename__ = "transcripts"

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segments: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Which pipeline stage last touched this row (TRANSCRIPTION → CLEANING).
    status: Mapped[StageName] = mapped_column(
        stage_name_enum, nullable=False, default=StageName.TRANSCRIPTION
    )

    job: Mapped["Job"] = relationship(back_populates="transcript")  # noqa: F821
