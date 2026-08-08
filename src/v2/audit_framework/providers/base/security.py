from __future__ import annotations

from pathlib import Path
from typing import Any
import re


SENSITIVE_NAME_PATTERNS = (
    re.compile(
        pattern,
        re.IGNORECASE,
    )
    for pattern in (
        r"(^|[._-])secret([._-]|$)",
        r"(^|[._-])token([._-]|$)",
        r"(^|[._-])password([._-]|$)",
        r"(^|[._-])passwd([._-]|$)",
        r"(^|[._-])credentials?([._-]|$)",
        r"(^|[._-])private[_-]?key([._-]|$)",
        r"(^|[._-])api[_-]?key([._-]|$)",
        r"\.env($|\.)",
        r"\.pem$",
        r"\.key$",
        r"id_rsa",
    )
)


def looks_sensitive(
    path: Path,
) -> bool:
    name = path.name

    return any(
        pattern.search(name)
        for pattern
        in SENSITIVE_NAME_PATTERNS
    )


def validate_no_sensitive_files(
    package_dir: Path,
    relative_paths: list[str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    sensitive_paths = []

    for relative in relative_paths:
        path = package_dir / relative

        if looks_sensitive(path):
            sensitive_paths.append(relative)

    checks.append(
        {
            "check_id": "PROVIDER_NO_SECRETS",
            "domain": "SECURITY",
            "status": (
                "PASS"
                if not sensitive_paths
                else "FAIL"
            ),
            "blocking": True,
            "message": (
                "No sensitive filenames detected."
                if not sensitive_paths
                else (
                    "Potential sensitive files detected."
                )
            ),
            "evidence": sensitive_paths,
        }
    )

    return checks
