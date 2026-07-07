# syntax=docker/dockerfile:1
# Multi-stage build shared by the API and worker containers. A single image with
# two entrypoints keeps dependencies consistent across the API and every worker.

# ── Stage 1: builder — install dependencies into a virtualenv ──────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Build tooling for any packages without wheels.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app

# Install the project plus the hosted-provider SDKs (LLM + hosted ASR) into an
# isolated venv. faster-whisper (the `local-asr` extra) is intentionally omitted
# to keep the image small and builds fast — add it only for offline local_whisper.
# To build an image with offline ASR: change to  pip install ".[llm,local-asr]"
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install ".[llm]"

# ── Stage 2: runtime — slim image with ffmpeg and a non-root user ──────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# ffmpeg/ffprobe are required for audio validation and normalization.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY pyproject.toml ./pyproject.toml
COPY docker/entrypoint-api.sh docker/entrypoint-worker.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint-api.sh /usr/local/bin/entrypoint-worker.sh \
    && mkdir -p /data/audio && chown -R app:app /data /app

USER app

EXPOSE 8000

# Default to the API; the worker containers override the entrypoint in compose.
ENTRYPOINT ["entrypoint-api.sh"]
