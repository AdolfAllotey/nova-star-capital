"""Secure parsing and validation for JSON returned by LLM providers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

MAX_LLM_JSON_CHARS = 50_000


class LlmJsonValidationError(ValueError):
    """Raised when an LLM response is not valid for the expected contract."""


def _strip_markdown_fence(content: str) -> str:
    """Remove one optional outer Markdown code fence."""

    stripped = content.strip()

    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()

    if len(lines) < 3 or lines[-1].strip() != "```":
        raise LlmJsonValidationError(
            "Malformed Markdown code fence around LLM JSON response."
        )

    opening = lines[0].strip().lower()

    if opening not in {"```", "```json"}:
        raise LlmJsonValidationError(
            f"Unsupported Markdown fence language: {opening!r}."
        )

    return "\n".join(lines[1:-1]).strip()


def parse_llm_json_object(content: str) -> dict[str, Any]:
    """Parse an LLM response as a strict JSON object.

    Python expressions, literals and executable code are deliberately rejected.
    """

    if not isinstance(content, str):
        raise LlmJsonValidationError(
            "LLM response content must be a string."
        )

    if not content.strip():
        raise LlmJsonValidationError(
            "LLM response content is empty."
        )

    if len(content) > MAX_LLM_JSON_CHARS:
        raise LlmJsonValidationError(
            "LLM response exceeds the maximum accepted size."
        )

    normalized = _strip_markdown_fence(content)

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise LlmJsonValidationError(
            "LLM response is not valid JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise LlmJsonValidationError(
            "LLM response must be a JSON object."
        )

    return parsed


def require_string(
    payload: Mapping[str, Any],
    field: str,
    *,
    max_length: int = 10_000,
) -> str:
    value = payload.get(field)

    if not isinstance(value, str):
        raise LlmJsonValidationError(
            f"Field {field!r} must be a string."
        )

    value = value.strip()

    if not value:
        raise LlmJsonValidationError(
            f"Field {field!r} must not be empty."
        )

    if len(value) > max_length:
        raise LlmJsonValidationError(
            f"Field {field!r} exceeds maximum length."
        )

    return value


def require_string_list(
    payload: Mapping[str, Any],
    field: str,
    *,
    max_items: int,
    max_item_length: int = 2_000,
) -> list[str]:
    value = payload.get(field)

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
    ):
        raise LlmJsonValidationError(
            f"Field {field!r} must be a JSON array of strings."
        )

    if len(value) > max_items:
        raise LlmJsonValidationError(
            f"Field {field!r} contains too many items."
        )

    result: list[str] = []

    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise LlmJsonValidationError(
                f"Field {field!r}[{index}] must be a string."
            )

        item = item.strip()

        if not item:
            raise LlmJsonValidationError(
                f"Field {field!r}[{index}] must not be empty."
            )

        if len(item) > max_item_length:
            raise LlmJsonValidationError(
                f"Field {field!r}[{index}] exceeds maximum length."
            )

        result.append(item)

    return result
