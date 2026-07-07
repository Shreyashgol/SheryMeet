"""Local filesystem implementation of the ObjectStorage port.

Keys are treated as relative paths under a configured base directory. Path
traversal is prevented by rejecting any key that resolves outside the base dir.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import BinaryIO

from app.storage.base import ObjectStorage


class LocalFileStorage(ObjectStorage):
    """Store objects on the local filesystem under `base_dir`."""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resolve a key to an absolute path, guarding against traversal."""
        candidate = (self._base / key).resolve()
        if not str(candidate).startswith(str(self._base)):
            raise ValueError(f"Invalid storage key (path traversal): {key!r}")
        return candidate

    def save(self, key: str, stream: BinaryIO) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            shutil.copyfileobj(stream, fh)
        return key

    def open(self, key: str) -> BinaryIO:
        return open(self._resolve(key), "rb")

    def local_path(self, key: str) -> str:
        return str(self._resolve(key))

    def delete(self, key: str) -> None:
        try:
            os.remove(self._resolve(key))
        except FileNotFoundError:
            pass  # idempotent

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()
