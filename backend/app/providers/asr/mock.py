"""Deterministic mock ASR provider for tests and offline development.

Returns a canned transcript so the full pipeline can be exercised without a real
model or GPU. If a sidecar `<audio>.transcript.txt` file exists, its contents are
used, which lets pipeline tests supply fixture-specific transcripts.
"""

from __future__ import annotations

import os

from app.providers.asr.base import ASRProvider, ASRResult, TranscriptSegment

_DEFAULT_TEXT = (
    "Alright everyone, thanks for joining. Um, so today we need to finalize the "
    "Q3 roadmap. John will own the API migration and it should be done by next "
    "Friday. There's a risk that the vendor contract slips. Sarah, please follow "
    "up with legal. We also decided to postpone the mobile release."
)


class MockASRProvider(ASRProvider):
    """A no-dependency ASR provider returning deterministic output."""

    name = "mock"

    def transcribe(self, audio_path: str, *, language: str | None = None) -> ASRResult:
        sidecar = f"{audio_path}.transcript.txt"
        if os.path.isfile(sidecar):
            with open(sidecar, encoding="utf-8") as fh:
                text = fh.read().strip()
        else:
            text = _DEFAULT_TEXT
        return ASRResult(
            text=text,
            language=language or "en",
            segments=[TranscriptSegment(start=0.0, end=1.0, text=text)],
        )
