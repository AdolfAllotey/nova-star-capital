from pathlib import Path
import json

DATA = Path("/opt/nsc/data/preprod/documentation")
ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")
INDEX = DATA / "masterbook_index.json"
OUT = ROOT / "DOCUMENTATION_QUALITY_ISSUES.md"


def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    docs = idx.get("documents", [])

    missing_classification = [d for d in docs if d.get("classification") in ("", "unknown")]
    missing_status = [d for d in docs if d.get("status") in ("", "unknown")]
    too_short = [d for d in docs if int(d.get("word_count") or 0) < 80]

    lines = [
        "# Nova Star Capital",
        "# Documentation Quality Issues",
        "",
        "Status: Official Documentation",
        "Classification: Documentation Center",
        "",
        "---",
        "",
        f"Missing classification: {len(missing_classification)}",
        f"Missing status: {len(missing_status)}",
        f"Too short documents: {len(too_short)}",
        "",
        "# Missing Classification",
        "",
    ]

    for d in missing_classification:
        lines.append(f"- {d.get('filename')}")

    lines += ["", "# Missing Status", ""]

    for d in missing_status:
        lines.append(f"- {d.get('filename')}")

    lines += ["", "# Too Short Documents", ""]

    for d in too_short:
        lines.append(f"- {d.get('filename')} — {d.get('word_count')} words")

    lines += [
        "",
        "# Recommended Action",
        "",
        "Add missing metadata and enrich short generated documents progressively.",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("Quality issues report created:")
    print(OUT)


if __name__ == "__main__":
    main()
