"""Structured logging configuration.

We use `structlog` to emit machine-parseable, contextual logs. Every log line
carries structured key/value pairs (never interpolated prose), and pipeline code
binds the `job_id` (and stage) into the context so all lines for a job can be
correlated across API and workers.

In production `log_json=True` emits JSON for ingestion by a log platform; in local
dev a colourised console renderer is used for readability.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config.settings import get_settings

_configured = False


def configure_logging() -> None:
    """Idempotently configure stdlib logging and structlog.

    Safe to call from both the API process and each Celery worker process.
    """
    global _configured
    if _configured:
        return

    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)

    # Route stdlib logging (uvicorn, sqlalchemy, celery) through a single handler.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger, configuring logging on first use."""
    configure_logging()
    return structlog.get_logger(name)


def bind_job_context(job_id: str, **extra: object) -> None:
    """Bind the current job id (and optional extras) into the logging context.

    Uses contextvars, so bindings are isolated per async task / thread and appear
    automatically on every subsequent log line until cleared.
    """
    structlog.contextvars.bind_contextvars(job_id=job_id, **extra)


def clear_job_context() -> None:
    """Clear any bound contextual logging variables for the current context."""
    structlog.contextvars.clear_contextvars()
