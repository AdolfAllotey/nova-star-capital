from __future__ import annotations

from typing import Any, Iterable


def normalize_key(
    value: str,
) -> str:
    return (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def walk_values(
    payload: Any,
    path: str = "",
) -> Iterable[
    tuple[str, str, Any]
]:
    if isinstance(payload, dict):
        for raw_key, value in payload.items():
            key = str(raw_key)
            normalized = normalize_key(key)

            current_path = (
                f"{path}.{key}"
                if path
                else key
            )

            yield (
                current_path,
                normalized,
                value,
            )

            yield from walk_values(
                value,
                current_path,
            )

    elif isinstance(payload, list):
        for index, value in enumerate(
            payload
        ):
            current_path = (
                f"{path}[{index}]"
            )

            yield from walk_values(
                value,
                current_path,
            )


def find_first_value(
    payload: Any,
    candidate_keys: Iterable[str],
) -> tuple[Any, str | None]:
    expected = {
        normalize_key(key)
        for key in candidate_keys
    }

    for path, key, value in walk_values(
        payload
    ):
        if key in expected:
            return value, path

    return None, None


def find_all_values(
    payload: Any,
    candidate_keys: Iterable[str],
) -> list[tuple[Any, str]]:
    expected = {
        normalize_key(key)
        for key in candidate_keys
    }

    results: list[tuple[Any, str]] = []

    for path, key, value in walk_values(
        payload
    ):
        if key in expected:
            results.append(
                (value, path)
            )

    return results


def normalize_scalar(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return (
            "true"
            if value
            else "false"
        )

    return str(value).strip()


def normalize_upper(
    value: Any,
) -> str:
    return normalize_scalar(
        value
    ).upper()


def coerce_bool(
    value: Any,
) -> bool | None:
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False

    normalized = normalize_upper(value)

    if normalized in {
        "TRUE",
        "YES",
        "Y",
        "1",
        "ENABLED",
        "ACTIVE",
        "FROZEN",
    }:
        return True

    if normalized in {
        "FALSE",
        "NO",
        "N",
        "0",
        "DISABLED",
        "INACTIVE",
        "NOT_FROZEN",
        "DYNAMIC",
    }:
        return False

    return None


def contains_token(
    payload: Any,
    token: str,
) -> list[str]:
    target = token.upper()
    evidence: list[str] = []

    for path, _, value in walk_values(
        payload
    ):
        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            if target in str(
                value
            ).upper():
                evidence.append(path)

    return evidence
