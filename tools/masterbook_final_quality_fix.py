from pathlib import Path

ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")

metadata_targets = {
    "DOCUMENTATION_CENTER_REPORT.md": ("Official Documentation", "Documentation Center"),
    "DOCUMENTATION_QUALITY_ISSUES.md": ("Official Documentation", "Documentation Center"),
}

enrich_targets = {
    "02_GLOBAL_ARCHITECTURE.md": "It provides the structural reference for how NSC domains interact across trading, portfolio, risk, execution, data, governance and operations.",
    "04_DISCOVERY_FRAMEWORK.md": "It ensures that opportunities are discovered consistently before entering validation, scoring, ranking and portfolio decision workflows.",
    "05_PORTFOLIO_BRAIN.md": "It acts as the strategic allocation layer that connects market opportunities with capital preservation, risk control and long-term portfolio objectives.",
    "07_GOVERNANCE.md": "It defines how decisions, changes, exceptions and operational processes remain controlled, documented, auditable and aligned with NSC principles.",
    "11_INFRASTRUCTURE.md": "It provides the operational foundation required for reliable execution, monitoring, storage, backup, scheduling and platform resilience.",
    "18_POLICY_REGISTRY.md": "It centralizes platform policies so that governance, risk, execution, documentation and operational rules remain discoverable and maintainable.",
}

def ensure_meta(path: Path, status: str, classification: str):
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    if "Status:" not in text:
        lines.insert(2 if len(lines) > 2 else len(lines), f"Status: {status}")
    text = "\n".join(lines)

    if "Classification:" not in text:
        lines = text.splitlines()
        lines.insert(3 if len(lines) > 3 else len(lines), f"Classification: {classification}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def enrich(path: Path, addition: str):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if addition not in text:
        text = text.rstrip() + "\n\n# Additional Context\n\n" + addition + "\n"
        path.write_text(text, encoding="utf-8")

for name, (status, classification) in metadata_targets.items():
    p = ROOT / name
    if p.exists():
        ensure_meta(p, status, classification)

for name, addition in enrich_targets.items():
    p = ROOT / name
    if p.exists():
        enrich(p, addition)

print("Final quality fix applied.")
