"""Database engine and session management (synchronous).

A single synchronous SQLAlchemy engine is shared by the API (FastAPI runs sync
endpoints in a threadpool) and the Celery workers. Sync is deliberate: the
workers are CPU/IO-bound around ASR/LLM calls, not high-concurrency web handlers,
so a single session model keeps the codebase simple and avoids async/sync
duplication.

`SessionLocal` is the factory; `session_scope()` provides transactional
boundaries for services and workers; `get_db()` is the FastAPI dependency.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_pre_ping=_settings.db_pool_pre_ping,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session scope.

    Commits on success, rolls back on any exception, and always closes the
    session. Used by services and workers to wrap a unit of work.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session.

    The session is committed by `session_scope` semantics at the service layer;
    here we only guarantee the session is closed after the request.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_database() -> bool:
    """Return True if a trivial query succeeds (used by the readiness probe)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        log.warning("database_healthcheck_failed", error=str(exc))
        return False
