"""ASR via Groq's hosted Whisper (OpenAI-compatible audio endpoint).

Groq serves Whisper models (e.g. whisper-large-v3-turbo) through an
OpenAI-compatible `audio.transcriptions` API, so this provider reuses
`OpenAIWhisperProvider` and only overrides the identity (`name`) and base URL.
Fast, offloads transcription from local CPU, and shares the `GROQ_API_KEY`
already used by the Groq LLM provider.
"""

from __future__ import annotations

from app.providers.asr.openai_whisper import OpenAIWhisperProvider


class GroqWhisperProvider(OpenAIWhisperProvider):
    """Transcribe audio with Groq-hosted Whisper (OpenAI-compatible endpoint)."""

    name = "groq_whisper"

    def __init__(self, api_key: str, *, model: str, timeout: int, base_url: str) -> None:
        super().__init__(api_key, model=model, timeout=timeout, base_url=base_url)
