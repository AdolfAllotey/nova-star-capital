from pathlib import Path

ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")

DEFAULT_CLASSIFICATION = "Master Book Governance"
DEFAULT_STATUS = "Official Documentation"

TARGETS = [
    "00_EXECUTIVE_SUMMARY.md",
    "02_GLOBAL_ARCHITECTURE.md",
    "03_INVESTMENT_ENGINES.md",
    "04_DISCOVERY_FRAMEWORK.md",
    "05_PORTFOLIO_BRAIN.md",
    "07_GOVERNANCE.md",
    "11_INFRASTRUCTURE.md",
    "12_ALGORITHM_REGISTRY.md",
    "13_ALGORITHM_CATALOG.md",
    "14_ALGORITHM_DEPENDENCIES.md",
    "15_ENGINE_RESPONSIBILITY_MATRIX.md",
    "16_DECISION_FLOW.md",
    "17_DECISION_VETO_FRAMEWORK.md",
    "18_POLICY_REGISTRY.md",
    "19_DATA_DICTIONARY.md",
    "20_ENGINE_LIFECYCLE.md",
    "21_EVENT_MESSAGING_ARCHITECTURE.md",
    "CHANGELOG.md",
    "MASTER_BOOK_CLEANUP_NOTES.md",
    "MASTER_BOOK_LEGACY_00_16_AUDIT.md",
    "MASTER_BOOK_LEGACY_00_16_CONSOLIDATION_PLAN.md",
    "MASTER_BOOK_STATUS_REPORT.md",
    "MASTER_V6_AUDIT_SUMMARY.md",
    "README.md",
]

EMPTY_DOC_CONTENT = {
    "00_EXECUTIVE_SUMMARY.md": "This document provides the executive overview of Nova Star Capital Master Book V7. It summarizes the platform vision, architecture, governance principles, operational standards and production readiness framework.",
    "02_GLOBAL_ARCHITECTURE.md": "This document describes the global architecture of Nova Star Capital, including investment engines, portfolio management, risk controls, execution, monitoring, governance and supporting infrastructure.",
    "04_DISCOVERY_FRAMEWORK.md": "This document defines the discovery framework used to identify market opportunities across sources, exchanges, assets and signals before they enter the decision pipeline.",
    "05_PORTFOLIO_BRAIN.md": "This document describes the Portfolio Brain, responsible for portfolio allocation, exposure management, capital posture, diversification, regime adaptation and cross-asset decision support.",
    "07_GOVERNANCE.md": "This document defines the governance principles that ensure Nova Star Capital remains controlled, auditable, explainable and aligned with its investment and operational philosophy.",
    "11_INFRASTRUCTURE.md": "This document describes the infrastructure foundations supporting Nova Star Capital, including runtime services, storage, monitoring, scheduling, resilience and operational dependencies.",
}

def ensure_metadata(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    lines = text.splitlines()

    if not text.strip():
        title = path.stem.replace("_", " ").title()
        body = EMPTY_DOC_CONTENT.get(path.name, "This document is part of the Nova Star Capital Master Book and defines an official reference area of the platform.")
        text = f"""# Nova Star Capital
# {title}

Version: V1.0
Status: {DEFAULT_STATUS}
Classification: {DEFAULT_CLASSIFICATION}

---

# Purpose

{body}

---

# Scope

This document applies to the relevant Nova Star Capital architecture, governance, operations and platform components.

---

# Final Principle

Every Master Book document contributes to the long-term consistency, auditability and institutional quality of Nova Star Capital.
"""
        path.write_text(text, encoding="utf-8")
        return

    changed = False

    if "Status:" not in text:
        insert_at = 2 if len(lines) >= 2 else len(lines)
        lines.insert(insert_at, f"Status: {DEFAULT_STATUS}")
        changed = True

    text = "\n".join(lines)

    if "Classification:" not in text:
        lines = text.splitlines()
        insert_at = 3 if len(lines) >= 3 else len(lines)
        lines.insert(insert_at, f"Classification: {DEFAULT_CLASSIFICATION}")
        changed = True

    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

for name in TARGETS:
    p = ROOT / name
    if p.exists():
        ensure_metadata(p)

print("Master Book quality fixes applied.")
