"""ASR via the OpenAI Whisper API.

An alternative to local inference for environments that prefer a managed endpoint.
The `openai` SDK is imported lazily so this module is importable without the
optional 'llm' extra installed.
"""

from __future__ import annotations

from app.core.enums import StageName
from app.core.exceptions import (
    ASRTimeoutError,
    EmptyTranscriptError,
    PermanentError,
    TransientError,
)
from app.core.logging import get_logger
from app.providers.asr.base import ASRProvider, ASRResult

log = get_logger(__name__)


class OpenAIWhisperProvider(ASRProvider):
    """Transcribe audio using OpenAI's hosted Whisper model."""

    name = "openai_whisper"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "whisper-1",
        timeout: int = 1200,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise PermanentError(
                f"An API key is required for the {self.name} provider",
                stage=StageName.TRANSCRIPTION,
            )
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._base_url = base_url
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dep
            raise PermanentError(
                "openai package not installed; install the 'llm' extra",
                stage=StageName.TRANSCRIPTION,
            ) from exc
        # base_url lets OpenAI-compatible backends (e.g. Groq) reuse this client.
        self._client = OpenAI(api_key=self._api_key, timeout=self._timeout, base_url=self._base_url)

    def transcribe(self, audio_path: str, *, language: str | None = None) -> ASRResult:
        self._ensure_client()
        assert self._client is not None
        try:
            with open(audio_path, "rb") as fh:
                resp = self._client.audio.transcriptions.create(
                    model=self._model, file=fh, language=language
                )
        except Exception as exc:  # noqa: BLE001 - map SDK errors to domain errors
            self._raise_mapped(exc)

        text = (getattr(resp, "text", "") or "").strip()
        if not text:
            raise EmptyTranscriptError(
                f"{self.name} returned empty text", stage=StageName.TRANSCRIPTION
            )
        return ASRResult(text=text, language=language)

    def _raise_mapped(self, exc: Exception) -> None:
        """Translate SDK exceptions to the domain error hierarchy."""
        exc_name = exc.__class__.__name__.lower()
        message = str(exc)
        if "timeout" in exc_name or "timeout" in message.lower():
            raise ASRTimeoutError(
                f"{self.name} timed out", stage=StageName.TRANSCRIPTION
            ) from exc
        if "ratelimit" in exc_name or "connection" in exc_name or "apistatus" in exc_name:
            raise TransientError(
                f"{self.name} transient error: {message[:200]}", stage=StageName.TRANSCRIPTION
            ) from exc
        raise PermanentError(
            f"{self.name} error: {message[:200]}", stage=StageName.TRANSCRIPTION
        ) from exc
