"""`summaries` table — structured meeting intelligence (1:1 with a job).

The list-valued fields (agenda, key_decisions, risks, blockers, next_steps) are
stored as JSONB arrays. Action items are normalised into their own table rather
than embedded here (3NF), so they can be queried, filtered and updated
independently.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin


class Summary(UUIDMixin, TimestampMixin, Base):
    """The structured summary generated for a job."""

    __tablename__ = "summaries"

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    meeting_title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    agenda: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    key_decisions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    risks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    blockers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    next_steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Provenance of the generation (for reproducibility / auditing).
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)

    job: Mapped["Job"] = relationship(back_populates="summary")  # noqa: F821
    action_items: Mapped[list["ActionItem"]] = relationship(  # noqa: F821
        back_populates="summary", cascade="all, delete-orphan"
    )
