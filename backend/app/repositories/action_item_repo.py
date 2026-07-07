"""Repository for the `ActionItem` aggregate."""

from __future__ import annotations

import uuid
from typing import Sequence

from app.models.action_item import ActionItem
from app.repositories.base import BaseRepository
from app.schemas.llm_output import ActionItemSchema


class ActionItemRepository(BaseRepository[ActionItem]):
    """Data access for accountable action items (many per job)."""

    model = ActionItem

    def bulk_create(
        self,
        *,
        job_id: uuid.UUID,
        summary_id: uuid.UUID,
        items: Sequence[ActionItemSchema],
    ) -> list[ActionItem]:
        """Persist a batch of validated action items for a job.

        The schema layer guarantees each item is complete (owner/deadline/priority
        defaulted), so no incomplete row can reach the database.
        """
        rows = [
            ActionItem(
                job_id=job_id,
                summary_id=summary_id,
                owner=item.owner,
                task=item.task,
                deadline=item.deadline,
                priority=item.priority,
                status=item.status,
            )
            for item in items
        ]
        self.session.add_all(rows)
        self.session.flush()
        return rows

    def list_by_job(self, job_id: uuid.UUID) -> Sequence[ActionItem]:
        """Return all action items for a job, oldest first (stable order)."""
        return (
            self.session.query(ActionItem)
            .filter(ActionItem.job_id == job_id)
            .order_by(ActionItem.created_at.asc())
            .all()
        )
