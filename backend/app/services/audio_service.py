"""Audio validation and normalization service (Phase 6 support).

Owns the "is this genuinely usable audio?" decision and the transcode to the
ASR-friendly format. Depends on the storage port (to resolve the stored file) and
the audio utilities (ffprobe/ffmpeg). Raises domain errors that classify the
failure as permanent (bad/unsupported/empty audio) so the worker fails fast.
"""

from __future__ import annotations

import os

from app.config.settings import Settings
from app.core.logging import get_logger
from app.storage.base import ObjectStorage
from app.utils.audio import AudioInfo, ensure_supported, normalize_to_wav, probe_audio, sniff_format

log = get_logger(__name__)


class AudioService:
    """Validate and normalize uploaded audio prior to transcription."""

    def __init__(self, storage: ObjectStorage, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings

    def validate(self, storage_key: str, declared_format: str) -> AudioInfo:
        """Validate the stored audio file end-to-end.

        Confirms the declared format is supported, that the magic bytes agree, and
        that the stream decodes with a non-zero duration.

        Returns:
            AudioInfo with the probed duration.
        """
        ensure_supported(declared_format, self._settings.allowed_audio_formats)
        path = self._storage.local_path(storage_key)

        with open(path, "rb") as fh:
            header = fh.read(16)
        sniffed = sniff_format(header)
        if sniffed is None:
            from app.core.enums import StageName
            from app.core.exceptions import UnsupportedAudioError

            raise UnsupportedAudioError(
                "File content does not match a supported audio format",
                stage=StageName.VALIDATION,
            )

        info = probe_audio(path)
        log.info("audio_validated", format=declared_format, duration=info.duration_seconds)
        return info

    def normalize(self, storage_key: str) -> str:
        """Transcode the stored audio to 16 kHz mono WAV for ASR; return its path."""
        src_path = self._storage.local_path(storage_key)
        dst_path = f"{os.path.splitext(src_path)[0]}.normalized.wav"
        normalize_to_wav(src_path, dst_path)
        log.info("audio_normalized", src=os.path.basename(src_path))
        return dst_path
