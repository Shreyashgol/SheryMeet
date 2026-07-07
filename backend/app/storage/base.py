"""Object storage port (interface).

Business code depends on this abstraction, never on a concrete filesystem or cloud
SDK. Swapping local disk for S3/GCS later means adding one adapter and a factory
branch — no service or worker changes (Dependency Inversion, Open/Closed).
"""

from __future__ import annotations

import abc
from typing import BinaryIO


class ObjectStorage(abc.ABC):
    """Abstract binary object store keyed by opaque storage keys."""

    @abc.abstractmethod
    def save(self, key: str, stream: BinaryIO) -> str:
        """Persist a binary stream under `key`; return the storage key."""

    @abc.abstractmethod
    def open(self, key: str) -> BinaryIO:
        """Open a stored object for reading."""

    @abc.abstractmethod
    def local_path(self, key: str) -> str:
        """Return a local filesystem path for `key`.

        Required by tools (ffmpeg, Whisper) that read from disk. Cloud adapters
        implement this by downloading to a temp file.
        """

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        """Remove a stored object (idempotent)."""

    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if an object exists for `key`."""
