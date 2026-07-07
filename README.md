# SheryMeet - Meeting Intelligence Pipeline

An asynchronous, production-oriented pipeline that turns a meeting recording
(`.wav` / `.mp3`) into a **structured meeting summary** and an **accountable
checklist** of action items.

## Live demo

- **Web app (Vercel):** https://shery-meet.vercel.app/
- **API docs (Render):** https://sherymeet.onrender.com/docs

> Hosted on free tiers — the backend sleeps after ~15 min of inactivity, so the
> first request may take up to a minute to cold-start.

---

## Table of contents

- [Problem](#problem)
- [Proposed solution](#proposed-solution)
- [System architecture](#system-architecture)
- [Tech stack](#tech-stack)
- [Local setup](#local-setup)
- [Future implementation](#future-implementation)
- [Conclusion](#conclusion)

---

## Problem

Meetings are where decisions get made — and where they get lost. A one-hour
recording is a wall of unstructured audio: nobody wants to re-listen to it, the
action items slip through the cracks, and "who agreed to do what, by when"
evaporates the moment the call ends.

Writing up notes by hand is slow, inconsistent, and the first thing people skip
when they're busy. The result is a pile of recordings nobody revisits and
follow-ups nobody owns. What teams actually need from a meeting isn't the
recording — it's **a summary they can share and a checklist someone is
accountable for.**

---

## Proposed solution

SheryMeet turns a raw meeting recording into two things a team can act on:

1. **A structured summary** — meeting title, overview, agenda, key decisions,
   risks, blockers, and next steps.
2. **An accountable checklist** — action items where every row has an owner, a
   task, a deadline, a priority, and a status.

Upload audio → it is transcribed by an ASR model, the transcript is cleaned, and
an LLM produces **schema-validated JSON** → you get a shareable summary and a
checklist where nothing is left unattributed. The whole flow runs
**asynchronously**, so large recordings process in the background while the UI
shows live progress.

Every action item is guaranteed complete: unknown owner → `"Unknown"`, absent
deadline → `"Not Specified"`, status → `"Pending"`.

### API surface

Base path: `/api/v1`. Interactive docs at `/docs` (Swagger) and `/redoc`.

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| `POST` | `/jobs` | multipart `file` (wav/mp3) | `201 { job_id, status }` | 400 unsupported/empty · 503 broker down |
| `GET` | `/jobs/{id}` | — | `200 { job_id, status, progress, timestamps, error_stage?, error_message? }` | 404 |
| `GET` | `/jobs/{id}/result` | — | `200 { job_id, summary, checklist, metadata }` | 404 · 409 not ready |
| `GET` | `/health` · `/ready` | — | `200` (ready checks DB + broker) | 503 |

Errors use a consistent envelope: `{ "error": { "code", "message", "detail?" } }`.

**Result shape:**

```jsonc
{
  "job_id": "…",
  "summary": {
    "meeting_title": "Q3 Roadmap Finalization",
    "summary": "…",
    "agenda": ["…"], "key_decisions": ["…"],
    "risks": ["…"], "blockers": [], "next_steps": ["…"]
  },
  "checklist": [
    { "id": "…", "owner": "John", "task": "Complete the API migration",
      "deadline": "next Friday", "priority": "High", "status": "Pending" }
  ],
  "metadata": {
    "audio_format": "wav", "duration_seconds": 612.0, "language": "en",
    "llm_provider": "claude", "llm_model": "claude-opus-4-8",
    "latencies_ms": { "VALIDATION": 4200, "CLEANING": 12, "SUMMARIZATION": 1800, "CHECKLIST": 1500 },
    "total_pipeline_ms": 7600
  }
}
```

### Job states

```
QUEUED → VALIDATING → TRANSCRIBING → CLEANING → SUMMARIZING → EXTRACTING_ACTIONS → COMPLETED
                                              └──────────────── FAILED (any stage) ┘
```

`progress` is derived from status (0 → 100), so the API and workers never drift.
The client polls `GET /jobs/{id}` for status/progress, then `GET /jobs/{id}/result`.

---

## System architecture

Clean architecture with dependencies pointing inward (API → services → domain;
infrastructure injected). Volatile third-party SDKs (ASR, LLM, storage) sit behind
ports so they are swappable via configuration without touching business code.

```
┌──────────────────────────────────────────────────────────────┐
│  WEB TIER — React + TS + Vite + Tailwind (nginx)               │
│  Upload · live job progress (polling) · result viewer          │
│  Dark / Light / System theme via CSS-variable design tokens    │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST/JSON (CORS-scoped, /api proxy)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  API TIER — FastAPI (thin; no business logic)                  │
│  validate upload → create job → store file → enqueue chain     │
└───────────────┬────────────────────────────────┬─────────────┘
                │ enqueue                          │ read
                ▼                                  ▼
     ┌────────────────────┐            ┌────────────────────────┐
     │  Redis (broker)    │            │  PostgreSQL (job state, │
     │  per-queue routing │            │  transcripts, summaries,│
     └─────────┬──────────┘            │  actions, logs/metrics) │
               │ Celery chain          └────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────────┐
│  WORKER TIER — 4 single-responsibility workers, one per queue  │
│   audio.q      → validate + normalize + Whisper ASR            │
│   transcript.q → clean / normalize transcript                 │
│   summary.q    → LLM structured summary                        │
│   checklist.q  → LLM action-item extraction                    │
└───────────────────────────┬──────────────────────────────────┘
                            │ uses (ports & adapters)
                            ▼
   ASRProvider  → local_whisper | openai_whisper | mock
   LLMProvider  → claude | openai | gemini | mock
   ObjectStorage → local_fs (S3-ready)
```

**Why Postgres is the source of truth:** Celery result state is transient. A
business pipeline needs durable, queryable job state, so every stage transition
and metric is written to Postgres; Redis/Celery are orchestration only.

> **Deployment note (free tier):** with no Redis/worker available (e.g. Render
> free tier, `CELERY_TASK_ALWAYS_EAGER=true`), the dispatcher runs the four
> stages sequentially in-process on a background thread instead of a broker-backed
> chain — so the API still returns immediately and reports progress as each stage
> completes.

### Runtime flow

```
Client ─POST /jobs─▶ API: validate ext+size → store file → INSERT job(QUEUED)
                     → enqueue chain(audio → transcript → summary → checklist)
                     ◀─ { job_id, status: QUEUED }

Audio Worker      VALIDATING → deep validate (magic bytes + ffprobe) →
                  TRANSCRIBING → ffmpeg normalize → Whisper ASR → INSERT transcript
Transcript Worker CLEANING → filler removal / spacing / punctuation → UPDATE transcript
Summary Worker    SUMMARIZING → LLM (schema-validated JSON) → INSERT summary
Checklist Worker  EXTRACTING_ACTIONS → LLM action items → INSERT action_items → COMPLETED

Each stage writes ProcessingLogs (event, latency_ms). Any unrecoverable error →
FAILED (with error_stage + message); the chain aborts.

Client polls GET /jobs/{id} for status/progress, then GET /jobs/{id}/result.
```

Only the `job_id` flows between tasks; each worker re-reads its input from
Postgres/storage, which makes tasks **idempotent and retry-safe**.

### Folder structure

```
meeting-summarizer/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes + DI (thin HTTP layer)
│   │   ├── core/           # enums, exceptions, logging, metrics
│   │   ├── config/         # Pydantic settings (env-driven)
│   │   ├── workers/        # celery_app, dispatch, 4 stage workers, base
│   │   ├── database/       # base/mixins, session, Alembic migrations
│   │   ├── models/         # SQLAlchemy ORM (one file per table)
│   │   ├── schemas/        # Pydantic DTOs + LLM I/O contracts
│   │   ├── repositories/   # data access (only place touching the ORM)
│   │   ├── services/       # business logic (job, audio, transcription, …)
│   │   ├── providers/      # ports & adapters: asr/*, llm/*
│   │   ├── prompts/        # summary_prompt.py, checklist_prompt.py
│   │   ├── storage/        # ObjectStorage port + local adapter
│   │   └── utils/          # audio, json_repair, retry
│   ├── tests/              # unit · integration · pipeline (+ fixtures)
│   ├── docker/             # Dockerfile, entrypoint-api.sh, entrypoint-worker.sh
│   ├── alembic.ini · pyproject.toml · .env.example
├── frontend/               # React SPA (see frontend/README on build)
│   ├── src/ · index.html · vite/tailwind/ts config
│   └── docker/             # Dockerfile (vite build → nginx) + nginx.conf
├── docker-compose.yml      # postgres · redis · migrate · api · 4 workers · frontend
├── .env.example
└── README.md
```

### Database schema

Normalized (3NF). Every table carries a UUID primary key and `created_at` /
`updated_at`; `jobs` also tracks `status`, `progress`, and lifecycle timestamps.

| Table | Cardinality | Purpose |
|---|---|---|
| `jobs` | aggregate root | status/progress, audio metadata, error attribution, lifecycle timestamps |
| `transcripts` | 1:1 with job | `raw_text`, `cleaned_text`, `language`, `segments` (JSONB, diarization-ready) |
| `summaries` | 1:1 with job | title/summary + `agenda`/`key_decisions`/`risks`/`blockers`/`next_steps` (JSONB), provenance |
| `action_items` | N:1 with job/summary | owner/task/deadline/priority/status (non-null defaults enforce completeness) |
| `processing_logs` | N:1 with job | append-only audit trail + `latency_ms` (metrics store) |

Enums are native Postgres types (`job_status`, `stage_name`, `priority`,
`action_item_status`, `log_level`). Metrics (queue-wait, ASR/LLM latency, total
pipeline latency) are derived from `processing_logs.latency_ms` + job timestamps.

---

## Tech stack

- **Backend:** FastAPI · Celery · Redis · PostgreSQL · SQLAlchemy · Pydantic · Alembic
- **AI:** Whisper (local `faster-whisper` or OpenAI API) · Claude / OpenAI / Gemini (pluggable)
- **Frontend:** React · TypeScript · Vite · Tailwind · TanStack Query
- **Ops:** Docker · Docker Compose · structured logging · per-stage metrics
- **Deploy:** Vercel (SPA) · Render (Docker API, free tier) · Neon (serverless Postgres)

---

## Local setup

### Configuration / environment variables

All configuration is environment-driven; no secrets are hardcoded. Config lives
in **two files**: `backend/.env` (API, DB, providers, keys) and `frontend/.env`
(SPA API base URL). The database is **Neon** (serverless Postgres) — set its
connection string in `backend/.env`; there is no local Postgres container.

| Variable (file) | Default | Notes |
|---|---|---|
| `DATABASE_URL` (backend) | — | **Neon** DSN: `postgresql+psycopg2://user:pass@host/db?sslmode=require` (pooled host recommended). A bare `postgresql://` scheme is auto-corrected. |
| `VITE_API_URL` (frontend) | `/api/v1` | API base; `/api/v1` works behind the nginx/dev proxy |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker + result backend |
| `ASR_PROVIDER` | `local_whisper` | `local_whisper` \| `openai_whisper` \| `mock` |
| `ASR_MODEL` | `base` | faster-whisper model size |
| `LLM_PROVIDER` | `claude` | `claude` \| `openai` \| `gemini` \| `mock` |
| `LLM_MODEL` | `claude-opus-4-8` | model id for the selected provider |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` | — | required for the matching provider |
| `MAX_UPLOAD_BYTES` | `209715200` | 200 MB upload cap |
| `CORS_ALLOW_ORIGINS` | `http://localhost:8080` | comma-separated allowlist |
| `RETRY_MAX_ATTEMPTS` | `3` | transient-failure retry budget |

> **Fully offline:** set `ASR_PROVIDER=mock` and `LLM_PROVIDER=mock` to run the
> entire pipeline with no models or API keys — used by the test suite.

### Running with Docker

```bash
cp backend/.env.example backend/.env    # set DATABASE_URL (Neon) + provider key
cp frontend/.env.example frontend/.env  # default VITE_API_URL is fine

docker compose up --build
```

Then open:

- Frontend UI: <http://localhost:8080>
- API docs: <http://localhost:8000/docs>

Compose starts `redis`, a one-shot `migrate` (Alembic → Neon), the `api`, four
per-queue workers, and the `frontend`. The database is Neon (external), so no
Postgres container runs. Scale a stage independently, e.g.:

```bash
docker compose up --scale worker-summary=3
```

### Running locally (without Docker)

Requires Python 3.11+, `ffmpeg`, and running Postgres + Redis.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[llm,dev]"          # hosted providers (Groq/OpenAI/Claude/Gemini)
# pip install -e ".[llm,dev,local-asr]"   # add offline ASR (ASR_PROVIDER=local_whisper)

export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/meetings
export REDIS_URL=redis://localhost:6379/0
export LLM_PROVIDER=mock ASR_PROVIDER=mock   # or set real provider + API key

alembic upgrade head
uvicorn app.main:app --reload                        # API on :8000

# In separate shells — one worker per queue:
celery -A app.workers.celery_app.celery_app worker -Q audio.q      -c 1
celery -A app.workers.celery_app.celery_app worker -Q transcript.q -c 2
celery -A app.workers.celery_app.celery_app worker -Q summary.q    -c 2
celery -A app.workers.celery_app.celery_app worker -Q checklist.q  -c 2
```

Frontend:

```bash
cd frontend && npm install && npm run dev   # Vite dev server on :5173
```

### Testing

```bash
cd backend
export DATABASE_URL=… REDIS_URL=…        # a reachable Postgres (integration/pipeline)
pytest                                    # unit + integration + pipeline
```

- **Unit** — services, schemas, utils in isolation (no DB, no network).
- **Integration** — repositories against a real Postgres; API routes via `TestClient`.
- **Pipeline (E2E)** — the full Celery chain in eager mode with **mock ASR + LLM**,
  asserting the job reaches `COMPLETED` and the result is schema-valid.

Integration/pipeline tests self-skip when no database is reachable.

---

## Future implementation

Designed to be extended without modifying existing modules:

- **Speaker diarization** — `transcripts.segments` already carries an optional
  `speaker`; add a diarization step and a new stage/worker.
- **Meeting sentiment / keyword extraction** — additional post-summary stages.
- **Embedding storage + vector search + RAG** — index transcripts/summaries for
  semantic search across meetings.
- **Integrations** — Slack/email delivery of summaries, calendar enrichment.
- **S3/GCS storage** — implement the `ObjectStorage` port; no service changes.
- **Auth & multi-tenancy** — user scoping on jobs; API keys / OAuth.
- **Observability** — export the per-stage latency read model to Prometheus/OTel.
- **Webhooks / WebSocket** — push job completion instead of client polling.

---

## Conclusion

SheryMeet is a small but complete, production-oriented system: it takes a messy
real-world input (an audio recording) and returns something a team can actually
use (a shareable summary and an owned checklist), end to end, asynchronously.
