"""API data-transfer objects for jobs.

DTOs decouple the HTTP contract from the ORM models. Routes return these Pydantic
models (never ORM entities), so persistence changes cannot leak into the API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import JobStatus, StageName


class JobCreateResponse(BaseModel):
    """Response for `POST /jobs`."""

    job_id: uuid.UUID
    status: JobStatus


class JobTimestamps(BaseModel):
    """Lifecycle timestamps for a job."""

    created_at: datetime
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobStatusResponse(BaseModel):
    """Response for `GET /jobs/{id}`."""

    job_id: uuid.UUID
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    timestamps: JobTimestamps
    error_stage: StageName | None = None
    error_message: str | None = None


class ResultMetadata(BaseModel):
    """Observability + provenance metadata attached to a result."""

    model_config = ConfigDict(protected_namespaces=())

    audio_format: str
    duration_seconds: float | None = None
    language: str | None = None
    llm_provider: str
    llm_model: str
    latencies_ms: dict[str, int] = Field(default_factory=dict)
    total_pipeline_ms: int | None = None
