"""Integration tests for the API routes (validation and error paths)."""

from __future__ import annotations

import io
import uuid

from tests.conftest import requires_db


@requires_db
def test_health_endpoint(client) -> None:  # noqa: ANN001
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@requires_db
def test_rejects_unsupported_format(client) -> None:  # noqa: ANN001
    resp = client.post(
        "/api/v1/jobs", files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_request"


@requires_db
def test_rejects_empty_file(client) -> None:  # noqa: ANN001
    resp = client.post(
        "/api/v1/jobs", files={"file": ("empty.wav", io.BytesIO(b""), "audio/wav")}
    )
    assert resp.status_code == 400


@requires_db
def test_unknown_job_returns_404(client) -> None:  # noqa: ANN001
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "job_not_found"


@requires_db
def test_result_before_ready_returns_409(client, db_session) -> None:  # noqa: ANN001
    """Requesting the result of a job that has not COMPLETED returns 409."""
    from app.repositories.job_repo import JobRepository

    job = JobRepository(db_session).create(
        original_filename="pending.wav", storage_key="k", audio_format="wav", size_bytes=1
    )
    db_session.commit()

    result = client.get(f"/api/v1/jobs/{job.id}/result")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "result_not_ready"
