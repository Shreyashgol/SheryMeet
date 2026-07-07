"""Audio utilities: format sniffing, validation and normalization.

Validation is defence-in-depth: extension/MIME alone are not trusted. We sniff
magic bytes and probe the stream with ffprobe to confirm the file is genuinely
decodable audio with a non-zero duration. Normalization uses ffmpeg to produce the
16 kHz mono WAV that ASR models expect.

ffmpeg/ffprobe are invoked as subprocesses (available in the Docker image), which
avoids heavyweight Python audio dependencies and handles both wav and mp3.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass

from app.core.enums import StageName
from app.core.exceptions import InvalidAudioError, UnsupportedAudioError

# Magic-byte signatures for the supported formats.
_WAV_RIFF = b"RIFF"
_WAV_WAVE = b"WAVE"
_MP3_ID3 = b"ID3"


@dataclass(frozen=True)
class AudioInfo:
    """Probed audio metadata."""

    format: str
    duration_seconds: float


def sniff_format(header: bytes) -> str | None:
    """Return 'wav' or 'mp3' from a file header, or None if unrecognised.

    - WAV: 'RIFF' at offset 0 and 'WAVE' at offset 8.
    - MP3: 'ID3' tag, or an MPEG audio frame sync (0xFF 0xEy/0xFy).
    """
    if len(header) >= 12 and header[0:4] == _WAV_RIFF and header[8:12] == _WAV_WAVE:
        return "wav"
    if header[0:3] == _MP3_ID3:
        return "mp3"
    if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
        return "mp3"
    return None


def _ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def probe_audio(path: str) -> AudioInfo:
    """Probe an audio file with ffprobe; validate it is decodable and non-empty.

    Raises:
        InvalidAudioError: if the file cannot be probed or has zero duration.
    """
    if not _ffprobe_available():
        raise InvalidAudioError(
            "ffprobe is not installed; cannot validate audio", stage=StageName.VALIDATION
        )
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "json",
        path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - environment dependent
        raise InvalidAudioError("Audio probe timed out", stage=StageName.VALIDATION) from exc

    if proc.returncode != 0:
        raise InvalidAudioError(
            f"Audio is corrupt or undecodable: {proc.stderr.strip()[:200]}",
            stage=StageName.VALIDATION,
        )

    try:
        data = json.loads(proc.stdout)
        duration = float(data["format"]["duration"])
        streams = data.get("streams", [])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        raise InvalidAudioError("Could not read audio duration", stage=StageName.VALIDATION) from exc

    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not has_audio:
        raise InvalidAudioError("File contains no audio stream", stage=StageName.VALIDATION)
    if duration <= 0:
        raise InvalidAudioError("Audio has zero duration (empty)", stage=StageName.VALIDATION)

    fmt = "wav" if streams and any(s.get("codec_type") == "audio" for s in streams) else "unknown"
    return AudioInfo(format=fmt, duration_seconds=duration)


def ensure_supported(format_hint: str, allowed: list[str]) -> str:
    """Validate a format hint against the allow-list; return the normalised value.

    Raises:
        UnsupportedAudioError: if the format is not supported.
    """
    fmt = format_hint.lower().lstrip(".")
    if fmt not in allowed:
        raise UnsupportedAudioError(
            f"Unsupported audio format {fmt!r}; allowed: {allowed}", stage=StageName.VALIDATION
        )
    return fmt


def normalize_to_wav(src_path: str, dst_path: str, *, sample_rate: int = 16000) -> str:
    """Transcode any supported input to 16 kHz mono PCM WAV for ASR.

    Raises:
        InvalidAudioError: if ffmpeg fails to transcode the input.
    """
    if shutil.which("ffmpeg") is None:
        raise InvalidAudioError("ffmpeg is not installed", stage=StageName.VALIDATION)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src_path,
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-vn",
        dst_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise InvalidAudioError(
            f"Audio normalization failed: {proc.stderr.strip()[:200]}", stage=StageName.VALIDATION
        )
    return dst_path
