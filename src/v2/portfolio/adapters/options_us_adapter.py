import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_PATH = Path("/opt/nsc/data/preprod/options_v3")

DASHBOARD_PATH = BASE_PATH / "options_v3_dashboard.json"
POSITIONS_OPEN_PATH = BASE_PATH / "options_v3_positions.json"
POSITIONS_CLOSED_PATH = BASE_PATH / "options_v3_positions_closed.json"
PORTFOLIO_SELECTED_PATH = BASE_PATH / "options_v3_portfolio_selected.json"
POCKETS_PATH = Path("/opt/nsc/data/preprod/portfolio/pockets.json")
CAPITAL_STATE_PATH = Path("/opt/nsc/data/preprod/portfolio/capital_state.json")

OUTPUT_PATH = Path(
    "/opt/nsc/data/preprod/portfolio/inputs/"
    "options_us_portfolio_input.json"
)


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def latest_timestamp(values: List[Any]) -> Optional[datetime]:
    parsed = [parse_timestamp(value) for value in values]
    valid = [value for value in parsed if value is not None]

    if not valid:
        return None

    return max(valid)


def iso_or_none(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None

    return value.astimezone(timezone.utc).isoformat()


def build_payload() -> Dict[str, Any]:
    dashboard = load_json(DASHBOARD_PATH, {})
    positions_open = load_json(POSITIONS_OPEN_PATH, [])
    positions_closed = load_json(POSITIONS_CLOSED_PATH, [])
    portfolio_selected = load_json(PORTFOLIO_SELECTED_PATH, [])
    pockets_doc = load_json(POCKETS_PATH, {})
    capital_state = load_json(CAPITAL_STATE_PATH, {})

    if not isinstance(dashboard, dict):
        dashboard = {}

    if not isinstance(positions_open, list):
        positions_open = []

    if not isinstance(positions_closed, list):
        positions_closed = []

    if not isinstance(portfolio_selected, list):
        portfolio_selected = []

    pockets = (
        pockets_doc.get("pockets", {})
        if isinstance(pockets_doc, dict)
        else {}
    )
    options_pocket = (
        pockets.get("options_us", {})
        if isinstance(pockets, dict)
        else {}
    )
    options_budget_eur = safe_float(
        options_pocket.get("budget_eur")
    )
    total_capital_eur = safe_float(
        capital_state.get("total_capital_eur")
        or capital_state.get("capital_eur")
    )
    deployable_capital_eur = safe_float(
        capital_state.get("deployable_capital_eur")
    )
    target_weight = (
        options_budget_eur
        / deployable_capital_eur
        if deployable_capital_eur > 0
        else 0.0
    )

    dashboard_status = dashboard.get("status", {}) or {}
    kpis = dashboard.get("kpis", {}) or {}
    portfolio = dashboard.get("portfolio", {}) or {}
    positions_summary = dashboard.get("positions", {}) or {}

    pipeline_status = (
        dashboard_status.get("pipeline_status")
        or "unavailable"
    )

    mode = (
        dashboard_status.get("mode")
        or "UNAVAILABLE"
    )

    execution_allowed = False
    real_money_enabled = False
    selected_confidences = [
        safe_float(item.get("confidence"))
        for item in portfolio_selected
        if isinstance(item, dict) and item.get("confidence") is not None
    ]

    selected_scores = [
        safe_float(item.get("score"))
        for item in portfolio_selected
        if isinstance(item, dict) and item.get("score") is not None
    ]

    confidence = (
        sum(selected_confidences) / len(selected_confidences)
        if selected_confidences
        else 0.0
    )

    average_score = (
        sum(selected_scores) / len(selected_scores)
        if selected_scores
        else 0.0
    )

    # RC2 provenance contract:
    # performance must not be inferred from legacy synthetic PnL.
    certified_closed = [
        item
        for item in positions_closed
        if isinstance(item, dict)
        and item.get("pnl_eur") is not None
        and item.get("pnl_provenance_status")
        not in {
            "NO_CERTIFIED_OPTION_MARK_PROVENANCE",
            "LEGACY_SYNTHETIC_PNL_NON_CERTIFIED",
        }
    ]

    certified_open = [
        item
        for item in positions_open
        if isinstance(item, dict)
        and item.get("pnl_eur") is not None
        and item.get("pnl_provenance_status")
        not in {
            "NO_CERTIFIED_OPTION_MARK_PROVENANCE",
            "LEGACY_SYNTHETIC_PNL_NON_CERTIFIED",
        }
    ]

    performance_available = bool(
        certified_closed or certified_open
    )

    realized_pnl = (
        round(
            sum(float(item["pnl_eur"]) for item in certified_closed),
            2,
        )
        if certified_closed
        else None
    )

    unrealized_pnl = (
        round(
            sum(float(item["pnl_eur"]) for item in certified_open),
            2,
        )
        if certified_open
        else None
    )

    wins = sum(
        1 for item in certified_closed
        if float(item["pnl_eur"]) > 0
    )

    losses = sum(
        1 for item in certified_closed
        if float(item["pnl_eur"]) < 0
    )

    certified_closed_count = len(certified_closed)

    win_rate_pct = (
        round((wins / certified_closed_count) * 100.0, 2)
        if certified_closed_count > 0
        else None
    )

    operational_timestamp = latest_timestamp(
        [
            dashboard.get("ts"),
            *[
                item.get("ts")
                for item in portfolio_selected
                if isinstance(item, dict)
            ],
            *[
                item.get("opened_at")
                for item in positions_open
                if isinstance(item, dict)
            ],
            *[
                item.get("closed_at")
                for item in positions_closed
                if isinstance(item, dict)
            ],
        ]
    )

    now = datetime.now(timezone.utc)

    freshness_age_hours = None
    if operational_timestamp is not None:
        freshness_age_hours = round(
            max(
                0.0,
                (now - operational_timestamp.astimezone(timezone.utc))
                .total_seconds()
                / 3600.0,
            ),
            2,
        )

    safety_contract_ok = (
        mode == "SHADOW"
        and execution_allowed is False
        and real_money_enabled is False
    )

    pipeline_healthy = pipeline_status == "ok"

    enabled = bool(
        pipeline_healthy
        and safety_contract_ok
        and dashboard
        and options_budget_eur > 0
        and deployable_capital_eur > 0
        and target_weight > 0
    )

    opportunity_status = (
        "ACTIVE_SELECTION"
        if portfolio_selected
        else "NO_CURRENT_OPPORTUNITY"
    )

    payload = {
        "brick": "options_us",
        "enabled": enabled,
        "portfolio_role": "active_options",
        "signal_type": "active_simulated_allocation",
        "target_weight": round(target_weight, 6),
        "confidence": round(confidence, 4),
        "regime": "active_simulated",
        "opportunity_status": opportunity_status,
        "allocation": {
            "pocket": "options_us",
            "pocket_budget_eur": round(options_budget_eur, 2),
            "total_capital_eur": round(total_capital_eur, 2),
            "deployable_capital_eur": round(
                deployable_capital_eur,
                2,
            ),
            "global_target_weight": round(target_weight, 6),
            "internal_used_risk_eur": safe_float(
                portfolio.get("used_risk_eur")
            ),
            "internal_used_risk_pct": safe_float(
                portfolio.get("used_risk_pct")
            ),
            "internal_max_total_risk_eur": safe_float(
                portfolio.get("max_total_risk_eur")
            ),
            "internal_max_trade_risk_eur": safe_float(
                portfolio.get("max_trade_risk_eur")
            ),
        },
        "drivers": {
            "pipeline_status": pipeline_status,
            "mode": mode,
            "signals_total": safe_int(kpis.get("signals_total")),
            "candidates_raw": safe_int(kpis.get("candidates_raw")),
            "candidates_validated": safe_int(
                kpis.get("candidates_validated")
            ),
            "decisions_total": safe_int(kpis.get("decisions_total")),
            "approved_count": safe_int(kpis.get("approved_count")),
            "rejected_count": safe_int(kpis.get("rejected_count")),
            "selected_count": safe_int(
                portfolio.get("selected_count", len(portfolio_selected))
            ),
            "positions_open": safe_int(
                positions_summary.get("open", len(positions_open))
            ),
            "positions_closed": safe_int(
                positions_summary.get("closed", len(positions_closed))
            ),
            "average_selected_score": round(average_score, 4),
            "average_selected_confidence": round(confidence, 4),
            "wins": wins,
            "losses": losses,
            "win_rate_pct": win_rate_pct,
            "performance_available": performance_available,
            "performance_status": (
                "AVAILABLE_CERTIFIED"
                if performance_available
                else "UNAVAILABLE_NO_CERTIFIED_MARKET_VALUATION"
            ),
            "performance_provenance_status": (
                "CERTIFIED_OPTION_MARK_PROVENANCE"
                if performance_available
                else "NO_CERTIFIED_OPTION_MARK_PROVENANCE"
            ),
        },
        "risk_flags": {
            # options_us is a governed simulated portfolio brick.
            # The underlying Options V3 engine still runs in SHADOW mode.
            "shadow_mode": False,
            "runtime_shadow_mode": mode == "SHADOW",
            "simulation_mode": True,
            "runtime_mode": mode,
            "execution_blocked": execution_allowed is False,
            "real_money_disabled": real_money_enabled is False,
            "safety_contract_ok": safety_contract_ok,
            "pipeline_healthy": pipeline_healthy,
            "estimated_risk_open_eur": safe_float(
                portfolio.get("used_risk_eur")
            ),
            "used_risk_pct": safe_float(
                portfolio.get("used_risk_pct")
            ),
            "max_total_risk_eur": safe_float(
                portfolio.get("max_total_risk_eur")
            ),
            "realized_pnl_eur": realized_pnl,
            "unrealized_pnl_eur": unrealized_pnl,
            "operational_timestamp_stale": (
                freshness_age_hours is None
                or freshness_age_hours > 48
            ),
        },
        "freshness": {
            "operational_timestamp": iso_or_none(
                operational_timestamp
            ),
            "operational_age_hours": freshness_age_hours,
            "dashboard_timestamp": iso_or_none(
                parse_timestamp(dashboard.get("ts"))
            ),
            "freshness_source": (
                "dashboard_runtime_plus_selected_positions_and_closed_trades"
            ),
            "legacy_status_source_deprecated": True,
        },
        "inertia_profile": {
            "rebalance_frequency": "daily",
            "max_weight_change_per_cycle": 0.01,
            "min_threshold_to_rebalance": 0.005,
        },
        "execution_mode": "simulated_only",
        "execution_allowed": False,
        "real_money_enabled": False,
        "funding_pool": "ibkr_pool",
        "source_file": str(DASHBOARD_PATH),
        "source_files": {
            "dashboard": str(DASHBOARD_PATH),
            "positions_open": str(POSITIONS_OPEN_PATH),
            "positions_closed": str(POSITIONS_CLOSED_PATH),
            "portfolio_selected": str(PORTFOLIO_SELECTED_PATH),
        },
        "state_origin": "options_v3_active_options_adapter",
        "timestamp": iso_or_none(operational_timestamp),
    }

    return payload


def export_options_us_to_portfolio_input() -> Dict[str, Any]:
    """
    Build, persist and return the canonical Options US portfolio input.

    This is the Portfolio Adapter Layer entrypoint used by the
    global PREPROD master refresh.
    """
    payload = build_payload()
    save_json(OUTPUT_PATH, payload)
    return payload


if __name__ == "__main__":
    payload = export_options_us_to_portfolio_input()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
