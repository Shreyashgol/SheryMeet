"""Application ports (interfaces) implemented by outer layers.

Defining these Protocols in the service layer inverts the dependency: the
`JobService` depends on an abstraction it owns, and the Celery layer provides the
concrete implementation. This keeps the service unit-testable (inject a fake
dispatcher) and free of any Celery import.
"""

from __future__ import annotations

import uuid
from typing import Protocol


class PipelineDispatcher(Protocol):
    """Enqueues the asynchronous processing pipeline for a job."""

    def dispatch(self, job_id: uuid.UUID) -> None:
        """Schedule the full processing pipeline for `job_id`.

        Implementations must raise `BrokerUnavailableError` when the broker cannot
        be reached, so the API can surface a 503 without leaking Celery details.
        """
        ...
