"""Shared pytest fixtures.

Configures a hermetic test environment: mock ASR/LLM providers (no network),
Celery in eager mode (tasks run inline), a temp storage directory, and a schema
created/dropped around the session. Environment variables are set before the app
is imported so cached settings pick them up.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

# ── Configure the environment BEFORE importing application modules ───────────────
_TMP_STORAGE = tempfile.mkdtemp(prefix="mip-test-audio-")
os.environ.setdefault("ASR_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_JSON", "false")
os.environ.setdefault("STORAGE_LOCAL_DIR", _TMP_STORAGE)
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:55432/meetings"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:56379/0")

from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.models import *  # noqa: E402,F401,F403  (register all models on metadata)


def _database_available() -> bool:
    try:
        with engine.connect():
            return True
    except Exception:  # noqa: BLE001
        return False


DB_AVAILABLE = _database_available()
requires_db = pytest.mark.skipif(not DB_AVAILABLE, reason="database not reachable")


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    """Create the schema for the test session and drop it afterwards."""
    if not DB_AVAILABLE:
        yield
        return
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session() -> Iterator["SessionLocal"]:
    """Provide a repository-facing database session, rolled back per test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client():
    """Provide a FastAPI TestClient with Celery running eagerly (inline)."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.workers.celery_app import celery_app

    # Run tasks inline, but do NOT propagate task exceptions into apply_async —
    # this mirrors production, where a stage failure surfaces in the worker (and
    # the job is marked FAILED) rather than in the HTTP request that dispatched it.
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def sample_wav_path() -> str:
    """Path to the bundled sample WAV fixture."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "sample.wav")
