from pathlib import Path
import json

DATA = Path("/opt/nsc/data/preprod/documentation")
INDEX = DATA / "masterbook_index.json"
OUT = DATA / "coverage_report.json"

EXPECTED_DOMAINS = {
    "crypto": ["CRYPTO"],
    "equities": ["EQUITIES", "EQUITY"],
    "bonds": ["BONDS"],
    "metals": ["METALS", "PRECIOUS"],
    "options": ["OPTIONS"],
    "forex": ["FOREX"],
    "risk": ["RISK"],
    "execution": ["EXECUTION"],
    "portfolio": ["PORTFOLIO"],
    "governance": ["GOVERNANCE"],
    "ai": ["AI", "MODEL"],
    "documentation": ["DOCUMENTATION", "MASTER_BOOK"],
    "operations": ["OPERATIONS", "INCIDENT", "RUNBOOK"],
    "security": ["SECURITY", "CYBER"],
    "data": ["DATA"],
}


def build_coverage():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    filenames = [d["filename"].upper() for d in idx.get("documents", [])]

    coverage = {}
    covered = 0

    for domain, keywords in EXPECTED_DOMAINS.items():
        matches = [f for f in filenames if any(k in f for k in keywords)]
        status = "covered" if matches else "missing"
        if matches:
            covered += 1
        coverage[domain] = {
            "status": status,
            "matches_count": len(matches),
            "matches": matches[:20],
        }

    score = round(covered / len(EXPECTED_DOMAINS) * 100, 2)

    payload = {
        "coverage_score": score,
        "covered_domains": covered,
        "total_domains": len(EXPECTED_DOMAINS),
        "domains": coverage,
    }

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


if __name__ == "__main__":
    payload = build_coverage()
    print("Coverage score:", payload["coverage_score"])
    print(OUT)
