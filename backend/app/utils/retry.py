"""Shared retry policy for transient failures.

Wraps `tenacity` with the application's configured backoff so provider adapters
retry only on `TransientError` (network blips, timeouts, rate limits, 5xx) and
never on `PermanentError`. Centralising this keeps retry semantics consistent and
configurable via environment variables.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.config.settings import get_settings
from app.core.exceptions import TransientError
from app.core.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T")


def with_transient_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorate a callable to retry on `TransientError` with exponential backoff.

    Attempt count and backoff bounds come from application settings.
    """
    settings = get_settings()

    return retry(
        reraise=True,
        retry=retry_if_exception_type(TransientError),
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_random_exponential(
            multiplier=settings.retry_backoff_base_seconds,
            max=settings.retry_backoff_max_seconds,
        ),
    )(func)
