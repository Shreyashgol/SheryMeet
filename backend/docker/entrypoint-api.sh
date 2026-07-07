#!/usr/bin/env bash
# API entrypoint: apply database migrations, then serve the FastAPI app.
set -euo pipefail

echo "[api] applying database migrations..."
alembic upgrade head

echo "[api] starting uvicorn on port ${PORT:-8000}..."
# Respect $PORT when provided (Render and most PaaS inject it); default to 8000.
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${API_WORKERS:-2}" \
    --proxy-headers
