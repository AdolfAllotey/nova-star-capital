from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")
MANIFEST = ROOT / "masterbook_manifest.json"


def slug(title: str) -> str:
    s = title.upper()
    s = re.sub(r"[^A-Z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def template(number: int, title: str, classification: str) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    return f"""# Nova Star Capital
# {title}

Version: V1.0
Status: Draft
Classification: {classification}
Created UTC: {today}

---

# Purpose

This document defines the official {title.lower()} for Nova Star Capital.

---

# Scope

This document applies to the relevant Nova Star Capital components, processes, controls and governance workflows.

---

# Objectives

The objectives are to ensure:

- consistency
- auditability
- operational discipline
- controlled execution
- long-term maintainability

---

# Principles

The following principles apply:

- decisions must remain traceable
- processes must remain documented
- exceptions must remain justified
- controls must remain observable
- governance must remain enforceable

---

# Standard Process

The standard process follows:

1. Identification
2. Assessment
3. Validation
4. Execution
5. Monitoring
6. Review
7. Documentation update

---

# Required Evidence

Required evidence may include:

- timestamps
- owners
- inputs
- outputs
- validation results
- decisions
- exceptions
- audit trail

---

# Governance

This document is governed by the Nova Star Capital Master Book.

Any material change requires:

- documentation update
- version update
- governance review when applicable

---

# Final Principle

Institutional quality is achieved through repeatable, observable and governed processes.
"""


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    created = []
    skipped = []

    for collection in manifest.get("collections", []):
        start = int(collection["start"])
        classification = collection["classification"]
        documents = collection.get("documents", [])

        for offset, title in enumerate(documents):
            number = start + offset
            filename = f"{number:03d}_{slug(title)}.md"
            path = ROOT / filename

            if path.exists():
                skipped.append(filename)
                continue

            path.write_text(template(number, title, classification), encoding="utf-8")
            created.append(filename)

    index_path = ROOT / "MASTER_BOOK_INDEX_AUTO.md"
    lines = [
        "# Nova Star Capital",
        "# Master Book Auto Index",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "---",
        "",
    ]

    for md in sorted(ROOT.glob("*.md")):
        lines.append(f"- [{md.name}](./{md.name})")

    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("MASTER BOOK GENERATION COMPLETE")
    print(f"Created: {len(created)}")
    print(f"Skipped existing: {len(skipped)}")
    print(f"Index: {index_path}")
    if created:
        print("\nCreated files:")
        for f in created:
            print(f" - {f}")


if __name__ == "__main__":
    main()
