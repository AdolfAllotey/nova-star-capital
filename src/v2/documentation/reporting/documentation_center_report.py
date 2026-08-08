from pathlib import Path
import json

DATA = Path("/opt/nsc/data/preprod/documentation")
OUT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7/DOCUMENTATION_CENTER_REPORT.md")


def load(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main():
    idx = load("masterbook_index.json")
    cov = load("coverage_report.json")
    health = load("documentation_health.json")

    lines = [
        "# Nova Star Capital",
        "# Documentation Center Report",
        "",
        "Status: Official Documentation",
        "Classification: Documentation Center",
        "",
        "---",
        "",
        f"Documents indexed: {idx.get('documents_count', 0)}",
        f"Coverage score: {cov.get('coverage_score', 0)}%",
        f"Documentation health: {health.get('documentation_health', 0)}%",
        f"Status: {health.get('status', 'unknown')}",
        "",
        "# Coverage by Domain",
        "",
    ]

    for domain, info in cov.get("domains", {}).items():
        lines.append(f"- {domain}: {info.get('status')} ({info.get('matches_count')} matches)")

    lines += [
        "",
        "# Quality Signals",
        "",
        f"- Missing classification: {health.get('missing_classification', 0)}",
        f"- Missing status: {health.get('missing_status', 0)}",
        f"- Too short documents: {health.get('too_short_documents', 0)}",
        "",
        "# Final Principle",
        "",
        "The Master Book is now monitored as a platform asset.",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("Documentation Center report created:")
    print(OUT)


if __name__ == "__main__":
    main()
