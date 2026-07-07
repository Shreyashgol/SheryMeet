"""`action_items` table — the accountable checklist (N:1 with job/summary).

Each row is a single accountable task. Non-null constraints plus database
defaults enforce the invariant that an action item is never incomplete: unknown
owners default to "Unknown", absent deadlines to "Not Specified", status to
"Pending".
"""

from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ActionItemStatus, Priority
from app.database.base import Base, TimestampMixin, UUIDMixin

priority_enum = SAEnum(Priority, name="priority", native_enum=True, validate_strings=True)
action_status_enum = SAEnum(
    ActionItemStatus, name="action_item_status", native_enum=True, validate_strings=True
)


class ActionItem(UUIDMixin, TimestampMixin, Base):
    """A single accountable action item extracted from the meeting."""

    __tablename__ = "action_items"

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner: Mapped[str] = mapped_column(String(256), nullable=False, default="Unknown")
    task: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[str] = mapped_column(String(128), nullable=False, default="Not Specified")
    priority: Mapped[Priority] = mapped_column(priority_enum, nullable=False, default=Priority.MEDIUM)
    status: Mapped[ActionItemStatus] = mapped_column(
        action_status_enum, nullable=False, default=ActionItemStatus.PENDING
    )

    job: Mapped["Job"] = relationship(back_populates="action_items")  # noqa: F821
    summary: Mapped["Summary"] = relationship(back_populates="action_items")  # noqa: F821
