"""Prompt builder for structured meeting summarization.

Prompts are kept out of service code and versioned here so they can be iterated
on independently. The required JSON schema is embedded verbatim; the LLM is
instructed to return JSON only (no markdown, no prose), and its output is
validated against the same Pydantic schema on the way back.
"""

from __future__ import annotations

SUMMARY_SYSTEM_PROMPT = """\
You are a meeting intelligence engine. You read a raw meeting transcript and \
produce a single structured JSON object summarizing the meeting.

STRICT OUTPUT RULES:
- Output a single JSON object and NOTHING else.
- No markdown, no code fences, no commentary before or after the JSON.
- Use double quotes for all keys and string values.
- If information for a field is absent, use an empty string or empty array — never null.

The JSON object MUST match this schema exactly:
{
  "meeting_title": "string - a concise descriptive title",
  "summary": "string - a dense 3-6 sentence executive summary",
  "agenda": ["string - discussion topics, in order"],
  "key_decisions": ["string - concrete decisions made"],
  "risks": ["string - risks raised"],
  "blockers": ["string - blockers or impediments"],
  "next_steps": ["string - agreed follow-up steps"],
  "action_items": [
    {
      "owner": "string - person responsible, or 'Unknown'",
      "task": "string - the concrete task (never empty)",
      "deadline": "string - due date/time, or 'Not Specified'",
      "priority": "High | Medium | Low",
      "status": "Pending"
    }
  ]
}

Every action item MUST be complete: if the owner is unknown use "Unknown"; if no \
deadline is given use "Not Specified"; always set status to "Pending"."""


def build_summary_prompt(transcript: str) -> tuple[str, str]:
    """Return the (system, user) prompt pair for summarizing a transcript."""
    user = (
        "Summarize the following meeting transcript into the required JSON object.\n\n"
        "TRANSCRIPT:\n"
        f"{transcript}"
    )
    return SUMMARY_SYSTEM_PROMPT, user
