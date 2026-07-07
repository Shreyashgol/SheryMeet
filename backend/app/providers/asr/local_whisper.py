"""Local ASR via faster-whisper (CTranslate2 Whisper).

Runs entirely offline inside the container with no paid API. The heavy
`faster-whisper` dependency is imported lazily so the module can be imported (and
the provider registry built) even in environments where it is not installed —
only constructing/using this provider requires the dependency.
"""

from __future__ import annotations

from app.core.enums import StageName
from app.core.exceptions import ASRTimeoutError, EmptyTranscriptError, InvalidAudioError
from app.core.logging import get_logger
from app.providers.asr.base import ASRProvider, ASRResult, TranscriptSegment

log = get_logger(__name__)


class LocalWhisperProvider(ASRProvider):
    """Transcribe audio with a locally hosted faster-whisper model."""

    name = "local_whisper"

    def __init__(
        self,
        model_name: str,
        *,
        device: str = "cpu",
        compute_type: str = "int8",
        default_language: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._default_language = default_language
        self._model = None  # lazy-loaded on first use

    def _ensure_model(self) -> None:
        """Lazily construct the WhisperModel (import guarded for optional dep)."""
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise InvalidAudioError(
                "faster-whisper is not installed. Use a hosted ASR provider "
                "(ASR_PROVIDER=groq_whisper) or install the offline extra: "
                "pip install '.[local-asr]'",
                stage=StageName.TRANSCRIPTION,
            ) from exc
        log.info("loading_whisper_model", model=self._model_name, device=self._device)
        self._model = WhisperModel(
            self._model_name, device=self._device, compute_type=self._compute_type
        )

    def transcribe(self, audio_path: str, *, language: str | None = None) -> ASRResult:
        self._ensure_model()
        assert self._model is not None
        lang = language or self._default_language
        try:
            segments_iter, info = self._model.transcribe(
                audio_path, language=lang, vad_filter=True
            )
            segments = [
                TranscriptSegment(start=s.start, end=s.end, text=s.text.strip())
                for s in segments_iter
            ]
        except TimeoutError as exc:  # pragma: no cover - runtime dependent
            raise ASRTimeoutError("Whisper transcription timed out", stage=StageName.TRANSCRIPTION) from exc

        text = " ".join(s.text for s in segments).strip()
        if not text:
            raise EmptyTranscriptError(
                "Transcription produced no text (silent or unintelligible audio)",
                stage=StageName.TRANSCRIPTION,
            )
        return ASRResult(text=text, language=getattr(info, "language", lang), segments=segments)
