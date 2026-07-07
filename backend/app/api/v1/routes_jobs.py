"""Job API routes.

Thin HTTP layer: parse/validate the request shape, delegate to `JobService`, and
return DTOs. All business logic and error-to-HTTP mapping live elsewhere (service
layer and the app's exception handlers).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import get_job_service
from app.schemas.job import JobCreateResponse, JobStatusResponse
from app.schemas.result import JobResultResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _file_size(upload: UploadFile) -> int:
    """Determine the uploaded file's size without loading it into memory."""
    file = upload.file
    file.seek(0, 2)  # seek to end
    size = file.tell()
    file.seek(0)
    return size


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    file: UploadFile = File(..., description="Meeting audio (wav or mp3)"),
    service: JobService = Depends(get_job_service),
) -> JobCreateResponse:
    """Upload a meeting audio file and enqueue it for processing."""
    size = _file_size(file)
    return service.create_job(
        filename=file.filename or "upload",
        stream=file.file,
        size_bytes=size,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(
    job_id: uuid.UUID,
    service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    """Return the status, progress, and lifecycle timestamps for a job."""
    return service.get_status(job_id)


@router.get("/{job_id}/result", response_model=JobResultResponse)
def get_job_result(
    job_id: uuid.UUID,
    service: JobService = Depends(get_job_service),
) -> JobResultResponse:
    """Return the structured summary, accountable checklist, and metadata."""
    return service.get_result(job_id)
