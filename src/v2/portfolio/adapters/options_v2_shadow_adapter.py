import json
from pathlib import Path

INPUT_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_dashboard.json")
STATUS_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_status.json")
REPORT_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_daily_report.json")
OUTPUT_PATH = Path("/opt/nsc/data/preprod/portfolio/inputs/options_v2_portfolio_input.json")


def load_json(path: Path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_payload():
    dashboard = load_json(INPUT_PATH, {})
    status = load_json(STATUS_PATH, {})
    report = load_json(REPORT_PATH, {})

    kpis = dashboard.get("kpis", {}) or {}
    pipeline_status = status.get("status", "unknown")
    mode = status.get("mode", "unknown")

    realized = float(kpis.get("realized_pnl_eur", 0.0) or 0.0)
    unrealized = float(kpis.get("unrealized_pnl_eur", 0.0) or 0.0)
    open_positions = int(kpis.get("positions_open", 0) or 0)
    estimated_risk_open = float(kpis.get("estimated_risk_open_eur", 0.0) or 0.0)
    approved_candidates = int(kpis.get("candidates_approved", 0) or 0)
    total_candidates = int(kpis.get("candidates_total", 0) or 0)
    opportunity_conversion_pct = float(kpis.get("opportunity_conversion_pct", 0.0) or 0.0)

    blocker = (((report.get("blockers") or {}).get("top_rejection_reason")) or {}).get("reason", "unknown")

    confidence = 0.0
    if pipeline_status == "ok":
        confidence = 0.70
        if approved_candidates > 0:
            confidence += 0.10
        if realized > 0:
            confidence += 0.10
        if open_positions > 0:
            confidence += 0.05
        confidence = min(confidence, 0.95)

    payload = {
        "brick": "options_v2_shadow",
        "enabled": True,
        "portfolio_role": "shadow_overlay",
        "signal_type": "shadow_observation",
        "target_weight": 0.0,
        "confidence": round(confidence, 4),
        "regime": "shadow_mode",
        "allocation": {},
        "drivers": {
            "pipeline_status": pipeline_status,
            "mode": mode,
            "positions_open": open_positions,
            "positions_closed": int(kpis.get("positions_closed", 0) or 0),
            "trades_total": int(kpis.get("trades_total", 0) or 0),
            "candidates_total": total_candidates,
            "candidates_approved": approved_candidates,
            "opportunity_conversion_pct": opportunity_conversion_pct,
            "top_blocker": blocker
        },
        "risk_flags": {
            "shadow_mode": True,
            "execution_blocked": True,
            "estimated_risk_open_eur": estimated_risk_open,
            "realized_pnl_eur": realized,
            "unrealized_pnl_eur": unrealized
        },
        "inertia_profile": {
            "rebalance_frequency": "none",
            "max_weight_change_per_cycle": 0.0,
            "min_threshold_to_rebalance": 1.0
        },
        "execution_mode": "shadow_only",
        "funding_pool": "ibkr_pool",
        "source_file": str(INPUT_PATH),
        "timestamp": status.get("ts")
    }
    return payload


if __name__ == "__main__":
    payload = build_payload()
    save_json(OUTPUT_PATH, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
