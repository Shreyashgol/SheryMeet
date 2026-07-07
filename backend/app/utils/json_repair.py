"""Tolerant extraction of JSON objects from LLM text output.

Even when instructed to emit pure JSON, models occasionally wrap output in
markdown fences or add stray prose. This helper extracts the first balanced JSON
object so schema validation has the best chance of succeeding before we resort to
a re-prompt.
"""

from __future__ import annotations

import json
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract and parse the first balanced top-level JSON object from `text`.

    Strips markdown code fences, then scans for the first `{ ... }` with balanced
    braces (ignoring braces inside strings).

    Raises:
        ValueError: if no valid JSON object can be parsed.
    """
    cleaned = text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences if present.
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)
        cleaned = cleaned[1] if len(cleaned) > 1 else ""
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
        cleaned = cleaned.strip()

    # Fast path: whole string is JSON.
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Scan for the first balanced object, respecting string literals.
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM output")

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : i + 1]
                try:
                    result = json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise ValueError("Malformed JSON object in LLM output") from exc
                if not isinstance(result, dict):
                    raise ValueError("Top-level JSON is not an object")
                return result

    raise ValueError("Unbalanced JSON object in LLM output")
