"""ASR provider port (interface) and result type.

The transcription service depends only on `ASRProvider`, so speech-recognition
backends (local faster-whisper, OpenAI Whisper API, or a test mock) are fully
interchangeable and selectable via configuration.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class TranscriptSegment:
    """A single timestamped (optionally speaker-labelled) transcript segment."""

    start: float
    end: float
    text: str
    speaker: str | None = None

    def as_dict(self) -> dict:
        """Serialise to a JSON-storable dict for the `transcripts.segments` column."""
        return {"start": self.start, "end": self.end, "text": self.text, "speaker": self.speaker}


@dataclass
class ASRResult:
    """The outcome of a transcription."""

    text: str
    language: str | None = None
    segments: list[TranscriptSegment] = field(default_factory=list)

    def segments_as_dicts(self) -> list[dict]:
        """Return segments as JSON-storable dicts."""
        return [s.as_dict() for s in self.segments]


class ASRProvider(abc.ABC):
    """Abstract speech-to-text provider."""

    #: Human-readable provider name (for logs/metrics/provenance).
    name: str = "asr"

    @abc.abstractmethod
    def transcribe(self, audio_path: str, *, language: str | None = None) -> ASRResult:
        """Transcribe the audio file at `audio_path`.

        Implementations must translate backend-specific timeouts/errors into the
        application's `TransientError` / `PermanentError` hierarchy.
        """
