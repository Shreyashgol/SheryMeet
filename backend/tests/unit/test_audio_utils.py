"""Unit tests for audio format sniffing and support checks."""

from __future__ import annotations

import pytest

from app.core.exceptions import UnsupportedAudioError
from app.utils.audio import ensure_supported, sniff_format


def test_sniff_wav_header() -> None:
    header = b"RIFF\x00\x00\x00\x00WAVEfmt "
    assert sniff_format(header) == "wav"


def test_sniff_mp3_id3_header() -> None:
    assert sniff_format(b"ID3\x04\x00\x00") == "mp3"


def test_sniff_mp3_frame_sync() -> None:
    assert sniff_format(b"\xff\xfb\x90\x00") == "mp3"


def test_sniff_unknown_returns_none() -> None:
    assert sniff_format(b"\x00\x01\x02\x03") is None


def test_ensure_supported_normalizes_extension() -> None:
    assert ensure_supported(".WAV", ["wav", "mp3"]) == "wav"


def test_ensure_supported_rejects_unknown() -> None:
    with pytest.raises(UnsupportedAudioError):
        ensure_supported("flac", ["wav", "mp3"])
