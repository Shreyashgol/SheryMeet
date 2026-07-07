# SheryMeet: Meeting Intelligence Pipeline

An asynchronous, production-oriented pipeline that processes raw meeting recordings (`.wav` / `.mp3`) into structured summaries and accountable action-item checklists using Whisper ASR and LLMs.

---

## ⚡️ Key Links & Live Demo
* **Web Client (Vercel)**: [shery-meet.vercel.app](https://shery-meet.vercel.app/)
* **API Docs (Render)**: [sherymeet.onrender.com/docs](https://sherymeet.onrender.com/docs)
> [!NOTE]
> Hosted on free-tier services. The backend sleeps after 15 minutes of inactivity; the initial request may take up to 60 seconds to cold-start.

---

## 🏗️ System Architecture & Runtime Flow

### Ports & Adapters (Hexagonal Design)
The backend is structured using clean architecture, where business logic is isolated and external services (ASR, LLM, Object Storage) are injected via interfaces (ports).

```
┌──────────────────────────────────────────────────────────────┐
│  WEB TIER: React + TS + Vite + Tailwind (Nginx)              │
│  Uploads raw audio, polls job state, and renders results.     │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST/JSON (CORS-scoped /api proxy)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  API TIER: FastAPI (Thin Gateway)                            │
│  Validates payloads, creates job metadata, enqueues pipeline. │
└───────────────┬────────────────────────────────┬─────────────┘
                │ Enqueue                          │ Reads / Writes
                ▼                                  ▼
     ┌────────────────────┐            ┌────────────────────────┐
     │   Redis (Broker)   │            │ PostgreSQL (Neon)      │
     │  Task orchestration│            │ Single source of truth │
     └─────────┬──────────┘            │ for jobs and outputs   │
               │ Celery Chain          └────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────────┐
│  WORKER TIER: Distributed Celery Workers (4 queues)           │
│   • audio.q      ➔ ffprobe validation & Whisper ASR           │
│   • transcript.q ➔ clean, filler removal & formatting         │
│   • summary.q    ➔ LLM structured summary generation          │
│   • checklist.q  ➔ LLM action-item extraction                 │
└───────────────────────────┬──────────────────────────────────┘
                            │ Outward-facing adapters
                            ▼
      ASRProvider   ➔ local_whisper | openai_whisper | mock
      LLMProvider   ➔ claude | openai | gemini | mock
      ObjectStorage ➔ local_fs (S3-compatible API)
```

### Runtime Pipeline Lifecycle
```
QUEUED ──▶ VALIDATING ──▶ TRANSCRIBING ──▶ CLEANING ──▶ SUMMARIZING ──▶ EXTRACTING_ACTIONS ──▶ COMPLETED
                                    └─────────────────── (Any Stage Failure) ───────────▶ FAILED
```
* **Idempotency**: Celery tasks pass only the `job_id`. Workers fetch inputs and store outputs directly using PostgreSQL/storage.
* **Eager Mode Fallback**: If Celery/Redis are unavailable (e.g., local development or single-node free tiers), setting `CELERY_TASK_ALWAYS_EAGER=true` processes the pipeline synchronously in a background thread without broker dependencies.

---

## 🛠️ Tech Stack & Key Architectural Decisions
- **FastAPI**: Non-blocking asynchronous web frame with automatic OpenAPI document generation.
- **Celery & Redis**: Decoupled, multi-queue task processing allows computational scaling for heavy workloads (ASR/LLM) independent of the API gateway.
- **PostgreSQL (Neon)**: The single source of truth. Unlike standard Celery systems, all job states, execution logs, and output models are written to a relational DB to enable structured historical queries.
- **Strict JSON Enforcement**: Instructs LLMs to return strict JSON matching Pydantic schemas, backed by local AST-based JSON healing and a bounded single reprompt strategy on validation failures.

---

## 💾 Relational Database Schema (3NF)

| Table | Cardinality | Key Fields & Purpose |
| :--- | :--- | :--- |
| **`jobs`** | *Aggregate Root* | Status, progress %, file paths, runtime errors, and execution timestamps. |
| **`transcripts`** | `1:1` with `jobs` | Diarization-ready `raw_text`, `cleaned_text`, and parsed `segments` (JSONB). |
| **`summaries`** | `1:1` with `jobs` | `meeting_title`, `summary`, and structured arrays (`agenda`, `key_decisions`, `risks`, `blockers`). |
| **`action_items`** | `N:1` with `jobs` | Relational list of action items detailing `owner`, `task`, `deadline`, `priority`, and `status`. |
| **`processing_logs`**| `N:1` with `jobs` | Append-only execution audit trail tracking per-stage latency (`latency_ms`). |

---

## 🔌 API Reference Highlights
Base Path: `/api/v1`

| Method | Path | Request Body | Success Response | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`POST`** | `/jobs` | `multipart/form-data` | `201 { job_id, status }` | Uploads meeting recording (`.mp3` / `.wav`) |
| **`GET`** | `/jobs/{id}` | *None* | `200 { job_id, status, progress, ... }` | Polls current progress status and stage logs |
| **`GET`** | `/jobs/{id}/result`| *None* | `200 { summary, checklist, metadata }` | Returns fully processed summary and action items |
| **`GET`** | `/health` / `/ready` | *None* | `200` | Checks service, DB, and Redis broker availability |

### Standard Error Response Envelope
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Unsupported file format.",
    "detail": { "allowed": ["wav", "mp3"] }
  }
}
```

---

## 🚀 Local Quickstart

### Environment Configuration
Copy env templates and customize:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

| Key Environment Variable | Description / Valid Values |
| :--- | :--- |
| **`DATABASE_URL`** | Neon Connection DSN (using `postgresql+psycopg2://` driver) |
| **`REDIS_URL`** | Celery broker URI (e.g. `redis://localhost:6379/0`) |
| **`ASR_PROVIDER`** | `local_whisper` (requires local C++ runtime) \| `openai_whisper` \| `mock` |
| **`LLM_PROVIDER`** | `claude` (Anthropic) \| `openai` \| `gemini` \| `mock` |
| **`API_KEY` Variables**| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY` |

> [!TIP]
> **Fully Offline Development**: Set `ASR_PROVIDER=mock` and `LLM_PROVIDER=mock` to run the entire backend pipeline locally without external API dependencies.

---

### Option A: Run via Docker Compose (Recommended)
This spins up the Redis broker, API server, 4 separate worker services, and the React frontend:
```bash
docker compose up --build
```
* **Frontend Access**: `http://localhost:8080`
* **Swagger API Documentation**: `http://localhost:8000/docs`

---

### Option B: Local Run (No Docker)

#### 1. Setup Backend
Ensure Python 3.11+ and `ffmpeg` are installed locally.
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[llm,dev]" # For hosted ASR/LLMs
# pip install -e ".[llm,dev,local-asr]" # Optional: installs faster-whisper locally

# Apply migrations and launch local dev server
alembic upgrade head
uvicorn app.main:app --reload
```

#### 2. Start Celery Workers (Separate terminals)
```bash
celery -A app.workers.celery_app.celery_app worker -Q audio.q -c 1
celery -A app.workers.celery_app.celery_app worker -Q transcript.q -c 2
celery -A app.workers.celery_app.celery_app worker -Q summary.q -c 2
celery -A app.workers.celery_app.celery_app worker -Q checklist.q -c 2
```

#### 3. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing Suite
The suite tests components in isolation and performs E2E pipeline processing in Celery eager mode using Mock services:
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

A few deliberate design decisions hold it together:

- **Ports & adapters** for ASR/LLM/storage → swap Whisper local↔API and
  Claude↔OpenAI↔Gemini by config (Open/Closed, Dependency Inversion).
- **Per-queue workers** enforce single responsibility at the infrastructure
  level and let expensive stages (ASR, LLM) scale independently.
- **Typed error hierarchy** (`TransientError` vs `PermanentError`) drives retry
  decisions without string-matching; transient failures retry with backoff,
  permanent failures fail fast and abort the chain.
- **Same Pydantic schema** instructs the LLM (embedded JSON schema) and validates
  its response; invalid JSON gets a tolerant repair + one bounded reprompt.
- **Structured logging** (structlog) with `job_id` bound across API and workers.

The result is a codebase that reads as a reference for structuring an async AI
pipeline — durable job state, clean boundaries, and swappable models — and one
that is straightforward to extend along the directions above.
