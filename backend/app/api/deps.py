"""FastAPI dependency providers (composition root for the API).

Wires request-scoped collaborators — a database session, the object storage, and
the Celery pipeline dispatcher — into the `JobService`. Centralising construction
here keeps routes thin and makes the wiring trivial to override in tests.
"""

from __future__ import annotations

from typing import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.database.session import get_db
from app.services.job_service import JobService
from app.services.ports import PipelineDispatcher
from app.storage.base import ObjectStorage
from app.storage.factory import get_storage


def get_storage_dep() -> ObjectStorage:
    """Provide the configured object storage."""
    return get_storage()


def get_dispatcher() -> PipelineDispatcher:
    """Provide the Celery-backed pipeline dispatcher.

    Imported lazily so the API package does not import Celery task modules at
    import time (keeps the API startup path independent of worker code).
    """
    from app.workers.dispatch import CeleryPipelineDispatcher

    return CeleryPipelineDispatcher()


def get_settings_dep() -> Settings:
    """Provide application settings."""
    return get_settings()


def get_job_service(
    session: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage_dep),
    dispatcher: PipelineDispatcher = Depends(get_dispatcher),
    settings: Settings = Depends(get_settings_dep),
) -> Iterator[JobService]:
    """Provide a request-scoped `JobService` with its collaborators injected."""
    yield JobService(session=session, storage=storage, dispatcher=dispatcher, settings=settings)
