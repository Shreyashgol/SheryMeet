"""Transcription service (Phase 6).

Thin application-layer wrapper around the injected `ASRProvider`. Applies the
shared transient-retry policy and guarantees a non-empty transcript, translating
an empty result into a permanent `EmptyTranscriptError`.
"""

from __future__ import annotations

from app.core.enums import StageName
from app.core.exceptions import EmptyTranscriptError
from app.core.logging import get_logger
from app.providers.asr.base import ASRProvider, ASRResult
from app.utils.retry import with_transient_retry

log = get_logger(__name__)


class TranscriptionService:
    """Produce a raw transcript from an audio file using the configured ASR provider."""

    def __init__(self, provider: ASRProvider) -> None:
        self._provider = provider

    def transcribe(self, audio_path: str, *, language: str | None = None) -> ASRResult:
        """Transcribe `audio_path`, retrying transient failures.

        Raises:
            EmptyTranscriptError: if the transcript is empty after transcription.
        """
        transcribe = with_transient_retry(self._provider.transcribe)
        result = transcribe(audio_path, language=language)
        if not result.text.strip():
            raise EmptyTranscriptError(
                "Transcription produced no usable text", stage=StageName.TRANSCRIPTION
            )
        log.info("transcription_complete", provider=self._provider.name, chars=len(result.text))
        return result
