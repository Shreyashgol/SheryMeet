"""Lightweight timing utilities for observability.

The pipeline records per-stage latency (queue wait, ASR, LLM, total) into
`processing_logs`. This module provides a small, dependency-free stopwatch so
services and workers can measure durations without pulling in a metrics client.
An external metrics backend (Prometheus/OTel) can later consume these same values.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class Stopwatch:
    """A monotonic stopwatch measuring elapsed wall-clock time in milliseconds."""

    _start: float = field(default_factory=time.perf_counter)
    elapsed_ms: int | None = None

    def stop(self) -> int:
        """Freeze and return elapsed milliseconds since construction."""
        self.elapsed_ms = int((time.perf_counter() - self._start) * 1000)
        return self.elapsed_ms


@contextmanager
def measure() -> Iterator[Stopwatch]:
    """Context manager yielding a `Stopwatch`; `elapsed_ms` is set on exit.

    Example:
        with measure() as sw:
            do_work()
        latency_ms = sw.elapsed_ms
    """
    watch = Stopwatch()
    try:
        yield watch
    finally:
        if watch.elapsed_ms is None:
            watch.stop()
