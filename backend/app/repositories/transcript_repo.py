"""Repository for the `Transcript` aggregate."""

from __future__ import annotations

import uuid

from app.core.enums import StageName
from app.models.transcript import Transcript
from app.repositories.base import BaseRepository


class TranscriptRepository(BaseRepository[Transcript]):
    """Data access for transcripts (one per job)."""

    model = Transcript

    def create_raw(
        self,
        *,
        job_id: uuid.UUID,
        raw_text: str,
        language: str | None,
        segments: list | None,
    ) -> Transcript:
        """Persist the raw ASR output for a job."""
        transcript = Transcript(
            job_id=job_id,
            raw_text=raw_text,
            language=language,
            segments=segments,
            word_count=len(raw_text.split()),
            status=StageName.TRANSCRIPTION,
        )
        return self.add(transcript)

    def set_cleaned(self, transcript: Transcript, cleaned_text: str) -> Transcript:
        """Attach the cleaned transcript text and advance the stage marker."""
        transcript.cleaned_text = cleaned_text
        transcript.word_count = len(cleaned_text.split())
        transcript.status = StageName.CLEANING
        self.session.flush()
        return transcript

    def get_by_job(self, job_id: uuid.UUID) -> Transcript | None:
        """Return the transcript belonging to a job, or None."""
        return self.get_by(job_id=job_id)
