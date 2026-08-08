from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")

OUTPUT = DATA / "audits" / "master_to_bricks_audit.json"


BRICKS = {
    "crypto": [
        PREPROD / "trading/capital_allocation.json",
        PREPROD / "trading/open_positions.json",
        PREPROD / "trading/execution_plan.json",
        PREPROD / "risk/worst_trades.json",
    ],
    "equities_offensive": [
        PREPROD / "equities_offensive/state/state.json",
        PREPROD / "equities_offensive/signals/signals_v1.json",
        PREPROD / "equities_offensive/execution/execution_plan.json",
        PREPROD / "equities_offensive/ui/ui_bundle.json",
    ],
    "equities_defensive": [
        PREPROD / "defensive/defensive_state.json",
        DATA / "defensive/defensive_allocations.json",
    ],
    "bonds": [
        PREPROD / "bonds/bond_state.json",
        DATA / "bonds/bond_signal.json",
    ],
    "precious_metals": [
        PREPROD / "metals/metals_state.json",
        DATA / "metals/metals_signal.json",
    ],
    "options_us": [
        PREPROD / "options_v3/options_v3_dashboard.json",
        PREPROD / "options_v3/options_v3_positions.json",
        PREPROD / "options_v3/options_v3_portfolio.json",
    ],
    "portfolio": [
        PREPROD / "portfolio/portfolio_target.json",
        PREPROD / "portfolio/state/portfolio_state.json",
        DATA / "capital/portfolio_state_normalized.json",
    ],
    "capital_funding": [
        DATA / "capital/config/capital_context.json",
        DATA / "capital/enterprise_value.json",
        DATA / "capital/treasury_state.json",
        DATA / "capital/collateral_state.json",
        DATA / "capital/funding_plan.json",
    ],
    "risk_governance": [
        PREPROD / "governance_engine_pro.json",
        PREPROD / "analysis/governance_engine_pro.json",
        DATA / "capital/survival_state.json",
    ],
    "api_ui": [
        DATA / "capital/family_office_bundle.json",
    ],
}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path):
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"__error__": str(exc)}


def classify_file(path: Path):
    data = read_json(path)

    if data is None:
        return {"path": str(path), "exists": False, "status": "missing"}

    if isinstance(data, dict) and data.get("__error__"):
        return {"path": str(path), "exists": True, "status": "error", "error": data.get("__error__")}

    if data == {} or data == []:
        return {"path": str(path), "exists": True, "status": "empty"}

    return {"path": str(path), "exists": True, "status": "ok"}


def run():
    report = {
        "status": "ok",
        "engine": "master_to_bricks_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),
        "bricks": {},
    }

    for brick, paths in BRICKS.items():
        files = [classify_file(p) for p in paths]
        missing = sum(1 for f in files if f["status"] == "missing")
        empty = sum(1 for f in files if f["status"] == "empty")
        errors = sum(1 for f in files if f["status"] == "error")
        ok = sum(1 for f in files if f["status"] == "ok")

        if errors:
            status = "error"
        elif missing:
            status = "incomplete"
        elif empty:
            status = "warning"
        else:
            status = "ok"

        report["bricks"][brick] = {
            "status": status,
            "files_ok": ok,
            "files_missing": missing,
            "files_empty": empty,
            "files_error": errors,
            "files": files,
        }

    report["summary"] = {
        "bricks_total": len(report["bricks"]),
        "bricks_ok": sum(1 for b in report["bricks"].values() if b["status"] == "ok"),
        "bricks_warning": sum(1 for b in report["bricks"].values() if b["status"] == "warning"),
        "bricks_incomplete": sum(1 for b in report["bricks"].values() if b["status"] == "incomplete"),
        "bricks_error": sum(1 for b in report["bricks"].values() if b["status"] == "error"),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
