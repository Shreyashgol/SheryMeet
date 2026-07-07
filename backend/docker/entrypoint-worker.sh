#!/usr/bin/env bash
# Worker entrypoint: run a Celery worker bound to a single queue.
#
# WORKER_QUEUE selects which stage this container processes (audio.q,
# transcript.q, summary.q, checklist.q). Binding one queue per container enforces
# the "no worker does another worker's job" rule and lets each stage scale
# independently.
set -euo pipefail

QUEUE="${WORKER_QUEUE:?WORKER_QUEUE must be set (e.g. audio.q)}"
CONCURRENCY="${WORKER_CONCURRENCY:-2}"
NAME="${WORKER_NAME:-worker}"

echo "[worker] starting Celery worker for queue=${QUEUE} concurrency=${CONCURRENCY}"
exec celery -A app.workers.celery_app.celery_app worker \
    --queues "${QUEUE}" \
    --concurrency "${CONCURRENCY}" \
    --hostname "${NAME}@%h" \
    --loglevel INFO
