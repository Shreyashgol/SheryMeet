"""Storage factory — selects the ObjectStorage implementation from config.

Centralising construction here keeps the wiring in one place and lets callers
depend only on the `ObjectStorage` interface (Dependency Injection).
"""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import get_settings
from app.storage.base import ObjectStorage
from app.storage.local_fs import LocalFileStorage


@lru_cache
def get_storage() -> ObjectStorage:
    """Return the configured object storage singleton."""
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalFileStorage(settings.storage_local_dir)
    raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")
