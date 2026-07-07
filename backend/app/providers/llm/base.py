"""LLM provider port (interface) and request/response types.

Summarization and checklist extraction depend only on `LLMProvider`, so the
concrete model vendor (Claude, OpenAI, Gemini, or a test mock) is interchangeable
and configuration-driven. Providers accept a system + user prompt and must return
raw text; JSON parsing/validation is the caller's responsibility (single place).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class LLMRequest:
    """A single-turn LLM completion request."""

    system: str
    user: str
    max_tokens: int
    temperature: float


@dataclass
class LLMResponse:
    """The raw text completion plus provenance for auditing."""

    text: str
    provider: str
    model: str


class LLMProvider(abc.ABC):
    """Abstract large-language-model text completion provider."""

    #: Human-readable provider identifier (for provenance/logs).
    name: str = "llm"
    #: The concrete model id in use.
    model: str = ""

    @abc.abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a completion for `request`.

        Implementations must map vendor timeouts/rate-limits/5xx onto the
        application's `TransientError` subclasses and other failures onto
        `PermanentError`.
        """
