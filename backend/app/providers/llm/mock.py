"""Deterministic mock LLM provider for tests and offline development.

Returns schema-valid JSON so the summary and checklist stages can run without a
real model or API key. It inspects the prompt to decide whether a summary object
or a checklist object is expected, mirroring the two prompt types.
"""

from __future__ import annotations

import json

from app.providers.llm.base import LLMProvider, LLMRequest, LLMResponse

_SUMMARY_JSON = {
    "meeting_title": "Q3 Roadmap Finalization",
    "summary": "The team finalized the Q3 roadmap, assigned the API migration, and "
    "postponed the mobile release.",
    "agenda": ["Finalize Q3 roadmap", "Assign ownership", "Review risks"],
    "key_decisions": ["Postpone the mobile release", "Proceed with API migration"],
    "risks": ["Vendor contract may slip"],
    "blockers": [],
    "next_steps": ["John to complete API migration", "Sarah to follow up with legal"],
    "action_items": [
        {
            "owner": "John",
            "task": "Complete the API migration",
            "deadline": "next Friday",
            "priority": "High",
            "status": "Pending",
        },
        {
            "owner": "Sarah",
            "task": "Follow up with legal on the vendor contract",
            "deadline": "Not Specified",
            "priority": "Medium",
            "status": "Pending",
        },
    ],
}

_CHECKLIST_JSON = {"action_items": _SUMMARY_JSON["action_items"]}


class MockLLMProvider(LLMProvider):
    """A no-dependency LLM provider returning deterministic, valid JSON."""

    name = "mock"
    model = "mock-1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        text_lower = f"{request.system}\n{request.user}".lower()
        payload = _CHECKLIST_JSON if "action item" in text_lower and "summary" not in text_lower else _SUMMARY_JSON
        return LLMResponse(text=json.dumps(payload), provider=self.name, model=self.model)
