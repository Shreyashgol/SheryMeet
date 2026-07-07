"""Transcript normalization service (Phase 7).

Deterministic, dependency-free cleaning applied to raw ASR output before it is
sent to the LLM: filler-word removal, whitespace/spacing normalization, light
punctuation and sentence-boundary repair, while preserving speaker labels.

Kept separate from the ASR provider (single responsibility) so cleaning can be
tuned or swapped without touching transcription.
"""

from __future__ import annotations

import re

# Common conversational fillers removed as standalone words (case-insensitive).
_FILLER_WORDS = {
    "um",
    "uh",
    "erm",
    "hmm",
    "uhh",
    "umm",
    "er",
    "ah",
    "like",  # only removed as a standalone filler token, see _strip_fillers
    "you know",
    "i mean",
    "sort of",
    "kind of",
    "basically",
    "literally",
    "actually",
}

# Speaker label at line start, e.g. "John:" or "Speaker 1:".
_SPEAKER_LABEL = re.compile(r"^\s*([A-Z][\w .'-]{0,40}):\s*")
_MULTISPACE = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.!?;:])")
_REPEATED_PUNCT = re.compile(r"([,.!?;:])\1{1,}")


class CleaningService:
    """Normalize a raw transcript into clean, readable text."""

    def clean(self, raw_text: str) -> str:
        """Return a cleaned version of `raw_text`, preserving speaker labels.

        Processing is line-oriented so speaker labels (which anchor to line starts)
        are preserved while their spoken content is normalized.
        """
        lines = raw_text.splitlines() or [raw_text]
        cleaned_lines: list[str] = []
        for line in lines:
            speaker, content = self._split_speaker(line)
            content = self._strip_fillers(content)
            content = self._normalize_spacing(content)
            content = self._repair_punctuation(content)
            content = self._ensure_terminal_punctuation(content)
            if not content:
                continue
            cleaned_lines.append(f"{speaker}: {content}" if speaker else content)
        return "\n".join(cleaned_lines).strip()

    @staticmethod
    def _split_speaker(line: str) -> tuple[str | None, str]:
        """Separate a leading speaker label from the spoken content."""
        match = _SPEAKER_LABEL.match(line)
        if match:
            return match.group(1).strip(), line[match.end() :].strip()
        return None, line.strip()

    @staticmethod
    def _strip_fillers(text: str) -> str:
        """Remove standalone filler words/phrases without harming real content."""
        if not text:
            return text
        # Remove multi-word fillers first.
        for phrase in ("you know", "i mean", "sort of", "kind of"):
            text = re.sub(rf"\b{re.escape(phrase)}\b", " ", text, flags=re.IGNORECASE)
        # Remove single-word fillers token-wise.
        tokens = text.split()
        kept = [t for t in tokens if t.strip(".,!?").lower() not in _FILLER_WORDS]
        return " ".join(kept)

    @staticmethod
    def _normalize_spacing(text: str) -> str:
        """Collapse repeated whitespace and trim."""
        return _MULTISPACE.sub(" ", text).strip()

    @staticmethod
    def _repair_punctuation(text: str) -> str:
        """Repair spacing around punctuation and collapse repeated punctuation."""
        text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
        text = _REPEATED_PUNCT.sub(r"\1", text)
        return text

    @staticmethod
    def _ensure_terminal_punctuation(text: str) -> str:
        """Ensure a non-empty utterance ends with sentence-terminating punctuation."""
        if text and text[-1] not in ".!?":
            text = f"{text}."
        # Capitalize the first alphabetic character for a cleaner sentence boundary.
        for i, ch in enumerate(text):
            if ch.isalpha():
                return text[:i] + ch.upper() + text[i + 1 :]
        return text
