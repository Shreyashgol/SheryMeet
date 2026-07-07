"""Repository for the `Summary` aggregate."""

from __future__ import annotations

import uuid

from app.models.summary import Summary
from app.repositories.base import BaseRepository
from app.schemas.llm_output import MeetingSummary


class SummaryRepository(BaseRepository[Summary]):
    """Data access for structured meeting summaries (one per job)."""

    model = Summary

    def create_from_schema(
        self,
        *,
        job_id: uuid.UUID,
        data: MeetingSummary,
        provider: str,
        model: str,
    ) -> Summary:
        """Persist a validated `MeetingSummary` (excluding action items).

        Action items are normalised into their own table by the checklist stage,
        so they are intentionally not written here.
        """
        summary = Summary(
            job_id=job_id,
            meeting_title=data.meeting_title,
            summary=data.summary,
            agenda=data.agenda,
            key_decisions=data.key_decisions,
            risks=data.risks,
            blockers=data.blockers,
            next_steps=data.next_steps,
            provider=provider,
            model=model,
        )
        return self.add(summary)

    def get_by_job(self, job_id: uuid.UUID) -> Summary | None:
        """Return the summary belonging to a job, or None."""
        return self.get_by(job_id=job_id)
