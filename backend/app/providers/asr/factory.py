"""ASR provider factory — selects the transcription backend from configuration.

Callers depend on the `ASRProvider` interface and obtain a concrete instance here,
so switching between local Whisper, the OpenAI API, or the test mock is a pure
configuration change (Dependency Injection / Open-Closed).
"""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import get_settings
from app.providers.asr.base import ASRProvider
from app.providers.asr.mock import MockASRProvider


@lru_cache
def get_asr_provider() -> ASRProvider:
    """Return the configured ASR provider singleton.

    Real providers are imported lazily so their heavy/optional dependencies are
    only loaded when actually selected.
    """
    settings = get_settings()
    provider = settings.asr_provider

    if provider == "mock":
        return MockASRProvider()

    if provider == "local_whisper":
        from app.providers.asr.local_whisper import LocalWhisperProvider

        return LocalWhisperProvider(
            settings.asr_model,
            device=settings.asr_device,
            compute_type=settings.asr_compute_type,
            default_language=settings.asr_language,
        )

    if provider == "openai_whisper":
        from app.providers.asr.openai_whisper import OpenAIWhisperProvider

        return OpenAIWhisperProvider(
            settings.openai_api_key, timeout=settings.asr_timeout_seconds
        )

    if provider == "groq_whisper":
        from app.providers.asr.groq_whisper import GroqWhisperProvider

        return GroqWhisperProvider(
            settings.groq_api_key,
            model=settings.groq_whisper_model,
            timeout=settings.asr_timeout_seconds,
            base_url=settings.groq_base_url,
        )

    raise ValueError(f"Unsupported ASR provider: {provider}")
