"""Unit tests for tolerant JSON extraction from LLM output."""

from __future__ import annotations

import pytest

from app.utils.json_repair import extract_json_object


def test_parses_plain_json() -> None:
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_strips_markdown_fences() -> None:
    text = '```json\n{"a": 1, "b": [1,2]}\n```'
    assert extract_json_object(text) == {"a": 1, "b": [1, 2]}


def test_extracts_object_from_surrounding_prose() -> None:
    text = 'Here is the result:\n{"x": "y"}\nHope that helps!'
    assert extract_json_object(text) == {"x": "y"}


def test_handles_braces_inside_strings() -> None:
    text = '{"note": "use { and } carefully"}'
    assert extract_json_object(text) == {"note": "use { and } carefully"}


def test_raises_when_no_object() -> None:
    with pytest.raises(ValueError):
        extract_json_object("no json here")
