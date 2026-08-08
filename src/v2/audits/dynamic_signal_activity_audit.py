from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")

OUTPUT = DATA / "audits/dynamic_signal_activity_audit.json"
HISTORY_DIR = DATA / "audits/history/dynamic_signal_activity"

WATCHED_ARTIFACTS = {
    "portfolio_target": PREPROD / "portfolio/portfolio_target.json",
    "portfolio_state": PREPROD / "portfolio/state/portfolio_state.json",
    "execution_plan": PREPROD / "trading/execution_plan.json",
    "open_positions": PREPROD / "trading/open_positions.json",
    "governance_crypto": PREPROD / "analysis/governance_engine_pro.json",
    "risk_engine_crypto": DATA / "analysis/risk_engine_pro.json",
    "offensive_governance": DATA / "equities_offensive/governance/governance_engine_pro.json",
    "defensive_input": ROOT / "src/v2/data/portfolio/inputs/equities_defensive_portfolio_input.json",
    "bonds_input": ROOT / "src/v2/data/portfolio/inputs/bonds_portfolio_input.json",
    "metals_input": ROOT / "src/v2/data/portfolio/inputs/precious_metals_portfolio_input.json",
    "crypto_input": ROOT / "src/v2/data/portfolio/inputs/crypto_portfolio_input.json",
    "options_v3_dashboard": PREPROD / "options_v3/options_v3_dashboard.json",
    "options_v3_positions": PREPROD / "options_v3/options_v3_positions.json",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_bytes(path):
    try:
        if not path.exists():
            return None
        return path.read_bytes()
    except Exception:
        return None


def read_json(path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def content_hash(path):
    raw = read_bytes(path)
    if raw is None:
        return None
    return hashlib.sha256(raw).hexdigest()


def file_age_seconds(path):
    try:
        return round(datetime.now().timestamp() - path.stat().st_mtime)
    except Exception:
        return None


def extract_signal_fields(name, doc):
    if not isinstance(doc, dict):
        return {}

    fields = {}

    if name == "portfolio_target":
        fields = {
            "portfolio_regime": doc.get("portfolio_regime"),
            "final_brick_weights": doc.get("final_brick_weights"),
            "cash_buffer": doc.get("cash_buffer"),
            "brick_confidence": doc.get("brick_confidence"),
            "brick_regimes": doc.get("brick_regimes"),
        }

    elif name == "portfolio_state":
        bricks = doc.get("bricks") or {}
        fields = {
            "portfolio_regime": doc.get("portfolio_regime"),
            "bricks_confidence": {
                k: v.get("confidence")
                for k, v in bricks.items()
                if isinstance(v, dict)
            },
            "bricks_regime": {
                k: v.get("regime")
                for k, v in bricks.items()
                if isinstance(v, dict)
            },
            "bricks_weight": {
                k: v.get("target_weight_snapshot")
                for k, v in bricks.items()
                if isinstance(v, dict)
            },
        }

    elif name == "execution_plan":
        orders = doc.get("orders") or []
        fields = {
            "orders_count": len(orders),
            "order_symbols": [
                o.get("symbol") or o.get("token") or o.get("ticker")
                for o in orders if isinstance(o, dict)
            ],
            "order_modes": [
                o.get("execution_mode") or o.get("action_policy")
                for o in orders if isinstance(o, dict)
            ],
        }

    elif name == "open_positions":
        positions = doc.get("positions") if isinstance(doc, dict) else []
        if not isinstance(positions, list):
            positions = []
        fields = {
            "positions_count": len(positions),
            "symbols": [
                p.get("symbol") or p.get("token") or p.get("ticker")
                for p in positions if isinstance(p, dict)
            ],
        }

    elif name.startswith("options_v3"):
        fields = {
            "status": doc.get("status"),
            "kpis": doc.get("kpis"),
            "portfolio": doc.get("portfolio"),
            "positions_count": len(doc.get("positions") or []) if isinstance(doc.get("positions"), list) else None,
        }

    else:
        fields = {
            "status": doc.get("status"),
            "regime": doc.get("regime"),
            "confidence": doc.get("confidence"),
            "target_weight": doc.get("target_weight"),
            "portfolio_role": doc.get("portfolio_role"),
            "allocation": doc.get("allocation"),
            "hard_block": doc.get("hard_block"),
            "action_policy": doc.get("action_policy"),
            "mode": doc.get("mode"),
        }

    return fields


current = {
    "generated_at": utc_now(),
    "artifacts": {},
}

for name, path in WATCHED_ARTIFACTS.items():
    doc = read_json(path, {}) or {}
    current["artifacts"][name] = {
        "path": str(path),
        "exists": path.exists(),
        "age_seconds": file_age_seconds(path),
        "sha256": content_hash(path),
        "signals": extract_signal_fields(name, doc),
    }


previous_snapshots = sorted(HISTORY_DIR.glob("dynamic_signal_activity_*.json"))
previous = read_json(previous_snapshots[-1], {}) if previous_snapshots else {}

failed = []
activity = {}

prev_artifacts = previous.get("artifacts") if isinstance(previous, dict) else {}

for name, now_data in current["artifacts"].items():
    prev_data = prev_artifacts.get(name) if isinstance(prev_artifacts, dict) else None

    if not now_data.get("exists"):
        activity[name] = {
            "status": "missing",
            "hash_changed": None,
            "signals_changed": None,
        }
        failed.append({
            "check": "artifact_exists",
            "severity": "warning",
            "detail": "Watched artifact is missing.",
            "evidence": {"artifact": name, "path": now_data.get("path")},
        })
        continue

    if not prev_data:
        activity[name] = {
            "status": "new_baseline",
            "hash_changed": None,
            "signals_changed": None,
        }
        continue

    hash_changed = now_data.get("sha256") != prev_data.get("sha256")
    signals_changed = now_data.get("signals") != prev_data.get("signals")

    if hash_changed and signals_changed:
        status = "dynamic"
    elif hash_changed and not signals_changed:
        if name in {"portfolio_target", "portfolio_state", "execution_plan", "governance_crypto", "offensive_governance"}:
            status = "metadata_only_refresh"
        else:
            status = "fake_refresh_possible"
            failed.append({
                "check": "fake_refresh_possible",
                "severity": "warning",
                "detail": "Artifact hash changed but extracted signal fields did not change.",
                "evidence": {"artifact": name},
            })
    elif not hash_changed and not signals_changed:
        if name in {"portfolio_target", "portfolio_state"}:
            status = "expected_static"
        else:
            status = "unchanged"
    else:
        status = "dynamic"

    activity[name] = {
        "status": status,
        "hash_changed": hash_changed,
        "signals_changed": signals_changed,
    }


critical = [x for x in failed if x.get("severity") == "critical"]
warnings = [x for x in failed if x.get("severity") == "warning"]

result = {
    "generated_at": current["generated_at"],
    "status": "critical" if critical else "warning" if warnings else "ok",
    "engine": "dynamic_signal_activity_audit_v1",
    "summary": {
        "artifacts_watched": len(WATCHED_ARTIFACTS),
        "dynamic_count": len([x for x in activity.values() if x.get("status") == "dynamic"]),
        "unchanged_count": len([x for x in activity.values() if x.get("status") == "unchanged"]),
        "fake_refresh_possible_count": len([x for x in activity.values() if x.get("status") == "fake_refresh_possible"]),
        "missing_count": len([x for x in activity.values() if x.get("status") == "missing"]),
        "new_baseline_count": len([x for x in activity.values() if x.get("status") == "new_baseline"]),
    },
    "activity": activity,
    "failed_checks": failed,
    "notes": [
        "First run establishes baseline.",
        "Subsequent runs compare content hash and extracted signal fields.",
        "fake_refresh_possible means timestamp/content changed but business signals did not.",
    ],
    "artifacts": current["artifacts"],
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

HISTORY_DIR.mkdir(parents=True, exist_ok=True)
snapshot_path = HISTORY_DIR / f"dynamic_signal_activity_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
snapshot_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({
    "status": result["status"],
    "summary": result["summary"],
    "failed_checks": result["failed_checks"],
    "snapshot_written": str(snapshot_path),
}, indent=2, ensure_ascii=False))
