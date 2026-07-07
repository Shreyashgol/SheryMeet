"""End-to-end pipeline test.

Drives the full flow through the real API and the real Celery chain (eager),
with mock ASR and LLM providers so no external services are touched. Asserts the
job reaches COMPLETED and the result contains a schema-valid summary and
accountable checklist.
"""

from __future__ import annotations

from tests.conftest import requires_db


@requires_db
def test_full_pipeline_completes(client, sample_wav_path) -> None:  # noqa: ANN001
    with open(sample_wav_path, "rb") as fh:
        create = client.post(
            "/api/v1/jobs", files={"file": ("sample.wav", fh, "audio/wav")}
        )
    assert create.status_code == 201
    job_id = create.json()["job_id"]
    assert create.json()["status"] == "QUEUED"

    # With eager Celery, the chain has already run by the time POST returns.
    status = client.get(f"/api/v1/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "COMPLETED"
    assert status.json()["progress"] == 100

    result = client.get(f"/api/v1/jobs/{job_id}/result")
    assert result.status_code == 200
    body = result.json()

    # Summary shape
    summary = body["summary"]
    assert summary["meeting_title"]
    for field in ("agenda", "key_decisions", "risks", "blockers", "next_steps"):
        assert isinstance(summary[field], list)

    # Accountable checklist — every item is complete
    assert len(body["checklist"]) >= 1
    for item in body["checklist"]:
        assert item["owner"]
        assert item["task"]
        assert item["deadline"]
        assert item["priority"] in ("High", "Medium", "Low")
        assert item["status"] == "Pending"

    # Observability metadata
    meta = body["metadata"]
    assert meta["llm_provider"] == "mock"
    assert set(meta["latencies_ms"]).issuperset(
        {"VALIDATION", "CLEANING", "SUMMARIZATION", "CHECKLIST"}
    )
    assert meta["total_pipeline_ms"] is not None
