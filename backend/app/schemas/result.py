"""API DTOs for the meeting result (summary + checklist + metadata)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.core.enums import ActionItemStatus, Priority
from app.schemas.job import ResultMetadata


class ActionItemOut(BaseModel):
    """An action item as returned to clients."""

    id: uuid.UUID
    owner: str
    task: str
    deadline: str
    priority: Priority
    status: ActionItemStatus


class SummaryOut(BaseModel):
    """The structured summary as returned to clients (matches the LLM schema)."""

    meeting_title: str
    summary: str
    agenda: list[str]
    key_decisions: list[str]
    risks: list[str]
    blockers: list[str]
    next_steps: list[str]


class JobResultResponse(BaseModel):
    """Response for `GET /jobs/{id}/result`."""

    job_id: uuid.UUID
    summary: SummaryOut
    checklist: list[ActionItemOut]
    metadata: ResultMetadata
