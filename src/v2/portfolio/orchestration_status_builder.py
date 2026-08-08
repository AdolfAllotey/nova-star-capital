from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA = Path("/opt/nsc/data/preprod")

OPEN_POSITIONS_PATH = DATA / "trading" / "open_positions.json"
PORTFOLIO_STATE_PATH = DATA / "portfolio" / "state" / "portfolio_state.json"
REBALANCE_PLAN_PATH = DATA / "portfolio" / "rebalance" / "rebalance_plan.json"
FUNDING_PLAN_PATH = DATA / "portfolio" / "rebalance" / "funding_plan.json"
MASTER_AUDIT_PATH = DATA / "portfolio" / "audit" / "master_coherence_audit.json"

OUT = DATA / "portfolio" / "audit" / "orchestration_status.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except Exception:
        return None


def save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    audit = load(MASTER_AUDIT_PATH, {})
    rebalance = load(REBALANCE_PLAN_PATH, {})
    funding = load(FUNDING_PLAN_PATH, {})

    summary = audit.get("summary", {}) if isinstance(audit, dict) else {}

    errors = int(summary.get("errors_count", 0) or 0)
    warnings = int(summary.get("warnings_count", 0) or 0)
    missing_artifacts = summary.get("missing_artifacts") or []

    guardrail_status = "BLOCKING" if errors > 0 or missing_artifacts else ("WARNING" if warnings > 0 else "OK")

    paths = {
        "open_positions": OPEN_POSITIONS_PATH,
        "portfolio_state": PORTFOLIO_STATE_PATH,
        "rebalance_plan": REBALANCE_PLAN_PATH,
        "funding_plan": FUNDING_PLAN_PATH,
        "master_audit": MASTER_AUDIT_PATH,
    }

    mtimes = {k: mtime(v) for k, v in paths.items()}
    missing = [k for k, v in mtimes.items() if v is None]

    stale_items = []
    open_mtime = mtimes.get("open_positions")
    if open_mtime:
        for key in ["portfolio_state", "rebalance_plan", "funding_plan", "master_audit"]:
            artifact_mtime = mtimes.get(key)
            if artifact_mtime is None:
                stale_items.append(f"{key}:missing")
            elif artifact_mtime + 2 < open_mtime:
                stale_items.append(f"{key}:older_than_open_positions")

    stale_status = "BLOCKING" if missing or stale_items else "OK"

    orchestration_status = "OK"
    reasons = []

    if guardrail_status == "BLOCKING":
        orchestration_status = "BLOCKING"
        reasons.append("master_guardrail_blocking")

    if stale_status == "BLOCKING":
        orchestration_status = "BLOCKING"
        reasons.append("master_stale_blocking")

    if isinstance(rebalance, dict) and rebalance.get("status") != "ok":
        orchestration_status = "BLOCKING"
        reasons.append("rebalance_plan_not_ok")

    if isinstance(funding, dict) and funding.get("status") != "ok":
        orchestration_status = "BLOCKING"
        reasons.append("funding_plan_not_ok")

    if orchestration_status != "BLOCKING" and warnings > 0:
        orchestration_status = "WARNING"
        reasons.append("master_audit_warnings")

    if not reasons:
        reasons.append("all_master_checks_ok")

    payload = {
        "status": "ok",
        "engine": "orchestration_status_builder_v1",
        "env": "PREPROD",
        "generated_at": now(),
        "orchestration_status": orchestration_status,
        "orchestration_reasons": reasons,
        "master_guardrail_status": guardrail_status,
        "master_stale_status": stale_status,
        "master_stale_missing": missing,
        "master_stale_items": stale_items,
        "master_audit_status": audit.get("status") if isinstance(audit, dict) else None,
        "master_audit_errors": errors,
        "master_audit_warnings": warnings,
        "master_rebalance_status": rebalance.get("status") if isinstance(rebalance, dict) else None,
        "master_funding_status": funding.get("status") if isinstance(funding, dict) else None,
        "mtimes": mtimes,
        "sources": {k: str(v) for k, v in paths.items()},
    }

    save(OUT, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
