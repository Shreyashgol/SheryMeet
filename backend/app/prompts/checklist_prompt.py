"""Prompt builder for accountable action-item (checklist) extraction.

A dedicated prompt (separate from summarization) so the checklist worker can
extract action items independently — e.g. re-run extraction without re-summarizing.
The LLM returns JSON only; output is validated against the ActionItem schema.
"""

from __future__ import annotations

CHECKLIST_SYSTEM_PROMPT = """\
You are an accountability engine. You read a meeting transcript and extract every \
concrete, accountable action item as a single structured JSON object.

STRICT OUTPUT RULES:
- Output a single JSON object and NOTHING else.
- No markdown, no code fences, no commentary.
- Use double quotes for all keys and string values.

The JSON object MUST match this schema exactly:
{
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

RULES:
- Never produce an incomplete task. The "task" field must always be a concrete action.
- If the owner is unknown, set owner to "Unknown".
- If no deadline is stated, set deadline to "Not Specified".
- Always set status to "Pending".
- Infer priority from urgency and language; default to "Medium" when unclear.
- If there are no action items, return {"action_items": []}."""


def build_checklist_prompt(transcript: str) -> tuple[str, str]:
    """Return the (system, user) prompt pair for extracting action items."""
    user = (
        "Extract all accountable action items from the following meeting transcript "
        "into the required JSON object.\n\n"
        "TRANSCRIPT:\n"
        f"{transcript}"
    )
    return CHECKLIST_SYSTEM_PROMPT, user
