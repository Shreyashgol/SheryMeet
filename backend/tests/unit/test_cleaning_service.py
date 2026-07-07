"""Unit tests for the transcript cleaning service."""

from __future__ import annotations

from app.services.cleaning_service import CleaningService


def test_removes_filler_words() -> None:
    service = CleaningService()
    out = service.clean("Um, so uh we basically need to, you know, ship it.")
    assert "um" not in out.lower().split()
    assert "basically" not in out.lower()
    assert "ship it" in out.lower()


def test_preserves_speaker_labels() -> None:
    service = CleaningService()
    out = service.clean("John: uh we should ship\nSarah: agreed, um, yes")
    assert out.startswith("John:")
    assert "Sarah:" in out


def test_normalizes_spacing_and_punctuation() -> None:
    service = CleaningService()
    out = service.clean("we    ship  it   now !!")
    assert "    " not in out
    assert " !" not in out
    assert out.endswith("!") or out.endswith(".")


def test_capitalizes_and_terminates_sentence() -> None:
    service = CleaningService()
    out = service.clean("we ship it")
    assert out[0].isupper()
    assert out.endswith(".")


def test_drops_lines_that_are_only_fillers() -> None:
    service = CleaningService()
    out = service.clean("um uh hmm\nWe decided to proceed")
    assert "decided to proceed" in out.lower()
    assert out.lower().count("proceed") == 1
