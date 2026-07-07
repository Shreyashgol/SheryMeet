#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Run the whole system locally for development / debugging — minimal Docker.
#
#   ./run-local.sh                 # API + combined Celery worker + frontend
#   ./run-local.sh --no-frontend   # backend only
#   ./run-local.sh --api-only      # just the API (no worker) — pair with EAGER
#
# Uses your real backend/.env (Neon DB + Groq keys). The only infra dependency is
# Redis: this script reuses a running one, else starts a local `redis-server`,
# else falls back to a single Redis Docker container (stopped on exit).
#
# Ctrl+C tears everything down.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

RUN_FRONTEND=1
RUN_WORKER=1
for arg in "$@"; do
  case "$arg" in
    --no-frontend) RUN_FRONTEND=0 ;;
    --api-only)    RUN_WORKER=0; RUN_FRONTEND=0 ;;
    *) echo "unknown arg: $arg"; exit 2 ;;
  esac
done

PIDS=()
REDIS_CONTAINER=""

cleanup() {
  echo ""
  echo "→ shutting down..."
  for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  [ -n "$REDIS_CONTAINER" ] && docker stop "$REDIS_CONTAINER" >/dev/null 2>&1 || true
  echo "→ done."
}
trap cleanup EXIT INT TERM

# ── Preconditions ────────────────────────────────────────────────────────────
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
command -v ffmpeg  >/dev/null || echo "⚠  ffmpeg not found (needed for audio) — install with: brew install ffmpeg"

cd "$BACKEND"
PY="$BACKEND/.venv/bin/python"

# ── 1) Virtualenv + dependencies (self-healing) ──────────────────────────────
if [ ! -x "$PY" ]; then
  echo "→ creating virtualenv..."
  python3 -m venv .venv
fi
echo "→ installing backend dependencies (.[llm,dev])..."
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q -e ".[llm,dev]"

# ── 2) Redis (broker) ────────────────────────────────────────────────────────
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
redis_reachable() {
  "$PY" - <<'PYEOF'
import os, sys, redis
try:
    redis.Redis.from_url(os.environ["REDIS_URL"]).ping(); sys.exit(0)
except Exception:
    sys.exit(1)
PYEOF
}
if redis_reachable; then
  echo "→ redis: reachable"
elif command -v redis-server >/dev/null; then
  echo "→ redis: starting local redis-server"
  redis-server --daemonize yes >/dev/null
  sleep 1
elif command -v docker >/dev/null; then
  echo "→ redis: starting a Docker container (only Redis uses Docker)"
  REDIS_CONTAINER="$(docker run -d -p 6379:6379 redis:7-alpine)"
  sleep 2
else
  echo "✗ Redis is required. Install it (brew install redis) or Docker."; exit 1
fi

# ── 3) Storage dir + migrations (against Neon in backend/.env) ────────────────
export STORAGE_LOCAL_DIR="${STORAGE_LOCAL_DIR:-$BACKEND/data/audio}"
mkdir -p "$STORAGE_LOCAL_DIR"
echo "→ applying database migrations (Neon)..."
"$PY" -m alembic upgrade head

# ── 4) API (auto-reload) ─────────────────────────────────────────────────────
echo "→ starting API on http://localhost:8000 (reload)"
"$PY" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
PIDS+=($!)

# ── 5) One Celery worker consuming ALL queues (simplest to debug) ────────────
if [ "$RUN_WORKER" = 1 ]; then
  echo "→ starting Celery worker (all queues: audio,transcript,summary,checklist)"
  "$PY" -m celery -A app.workers.celery_app.celery_app worker \
    --queues audio.q,transcript.q,summary.q,checklist.q \
    --concurrency 4 --loglevel INFO &
  PIDS+=($!)
fi

# ── 6) Frontend (Vite dev server, proxies /api -> :8000) ─────────────────────
if [ "$RUN_FRONTEND" = 1 ]; then
  if command -v npm >/dev/null; then
    cd "$FRONTEND"
    [ -d node_modules ] || { echo "→ installing frontend deps..."; npm install; }
    echo "→ starting frontend on http://localhost:5173"
    npm run dev &
    PIDS+=($!)
    cd "$BACKEND"
  else
    echo "⚠  npm not found — skipping frontend (run it separately with: cd frontend && npm run dev)"
  fi
fi

echo ""
echo "──────────────────────────────────────────────"
echo "  API docs : http://localhost:8000/docs"
[ "$RUN_FRONTEND" = 1 ] && echo "  Frontend : http://localhost:5173"
echo "  Ctrl+C to stop everything"
echo "──────────────────────────────────────────────"
wait
