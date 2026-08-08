from __future__ import annotations
from pathlib import Path


OPTIONS_V3_PATH = Path("/opt/nsc/data/preprod/options_v3")

def _load_json_safe(path: Path, default=None):
    try:
        if path.exists():
            import json
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}

def load_options_v3_dashboard():
    return _load_json_safe(OPTIONS_V3_PATH / "options_v3_dashboard.json", {})

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(tags=["dashboard-v3"])

EQUITIES_UI_BUNDLE = Path("/opt/nsc/data/preprod/equities_offensive/ui/ui_bundle.json")
OFFENSIVE_EQUITY_CURVE_PATH = Path("/opt/nsc/data/preprod/equities_offensive/reporting/equity_curve.json")
DEFENSIVE_SIGNAL_PATH = Path("/opt/nsc/app/src/v2/data/defensive/defensive_signal.json")
DEFENSIVE_STATE_PATH = Path("/opt/nsc/data/preprod/defensive/defensive_state.json")
DEFENSIVE_EXPOSURE_PATH = Path("/opt/nsc/app/data/defensive/state/exposure_snapshot.json")
DEFENSIVE_FILLS_PATH = Path("/opt/nsc/app/data/defensive/execution/simulated_fills.jsonl")
PORTFOLIO_STATE_PATH = Path("/opt/nsc/data/preprod/portfolio/state/portfolio_state.json")
PORTFOLIO_TARGET_PATH = Path("/opt/nsc/data/preprod/portfolio/portfolio_target.json")
MASTER_COHERENCE_AUDIT_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/master_coherence_audit.json")
GLOBAL_ORCHESTRATION_AUDIT_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/global_orchestration_audit.json")
SUPERVISION_GATE_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/supervision_gate.json")
INSTITUTIONAL_SUPERVISION_SUMMARY_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/institutional_supervision_summary.json")
GLOBAL_PREPROD_STRESS_TESTS_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_stress_test_report.json")
GLOBAL_PREPROD_HISTORY_SUMMARY_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_history_summary.json")
GLOBAL_PREPROD_TREND_MONITOR_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_trend_monitor.json")
GLOBAL_PREPROD_ANOMALY_DETECTOR_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_anomaly_detector.json")
GLOBAL_PREPROD_LONG_RUN_READINESS_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_long_run_readiness.json")
GLOBAL_PREPROD_LONG_RUN_DAILY_REPORT_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_long_run_daily_report.json")
GLOBAL_PREPROD_48H_SHADOW_SUPERVISOR_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_48h_shadow_supervisor.json")
MASTER_REBALANCE_PLAN_PATH = Path("/opt/nsc/data/preprod/portfolio/rebalance/rebalance_plan.json")
MASTER_FUNDING_PLAN_PATH = Path("/opt/nsc/data/preprod/portfolio/rebalance/funding_plan.json")
INITIAL_CAPITAL_PATH = Path("/opt/nsc/app/data/portfolio/initial_capital.json")
CRYPTO_SIMULATION_PATH = Path("/opt/nsc/data/preprod/trading/trade_simulation.json")
CRYPTO_SIGNAL_CANDIDATES_PATH = Path("/opt/nsc/data/preprod/analysis/signal_candidates.json")
CRYPTO_OPEN_POSITIONS_PATH = Path("/opt/nsc/data/preprod/trading/open_positions.json")
CRYPTO_EXECUTION_PLAN_PATH = Path("/opt/nsc/data/preprod/trading/execution_plan.json")
EQUITY_CURVE_STATE_PATH = Path("/opt/nsc/data/preprod/analysis/equity_curve_state.json")
CONFIDENCE_HISTORY_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/confidence_history.jsonl")
OPERATIONAL_CONFIDENCE_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/operational_confidence.json")
EXECUTION_CONFIDENCE_PATH = Path("/opt/nsc/data/preprod/portfolio/audit/execution_confidence.json")
PNL_STATE_PATH = Path("/opt/nsc/data/preprod/analysis/pnl_state.json")
TRADE_JOURNAL_STATE_PATH = Path("/opt/nsc/data/preprod/analysis/trade_journal_state.json")
OPTIONS_V3_CLOSED_PATH = Path("/opt/nsc/data/preprod/options_v3/options_v3_positions_closed.json")

BONDS_SIGNAL_PATH = Path("/opt/nsc/app/data/bonds/bond_signal.json")
BOND_STATE_PATH = Path("/opt/nsc/data/preprod/bonds/bond_state.json")
BONDS_STATE_PATH = BOND_STATE_PATH
BONDS_EXPOSURE_PATH = Path("/opt/nsc/app/data/bonds/state/exposure_snapshot.json")
BONDS_FILLS_PATH = Path("/opt/nsc/app/data/bonds/execution/simulated_fills.jsonl")
METALS_SIGNAL_PATH = Path("/opt/nsc/app/data/metals/metals_signal.json")
METALS_STATE_PATH = Path("/opt/nsc/data/preprod/metals/metals_state.json")
METALS_EXPOSURE_PATH = Path("/opt/nsc/app/data/metals/state/exposure_snapshot.json")
METALS_FILLS_PATH = Path("/opt/nsc/app/data/metals/execution/simulated_fills.jsonl")

OPTIONS_V2_DASHBOARD_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_dashboard.json")
OPTIONS_V2_STATUS_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_status.json")
OPTIONS_V2_DAILY_REPORT_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_daily_report.json")
OPTIONS_V2_TRADES_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_trades.json")
OPTIONS_V2_POSITIONS_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_positions.json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default



def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def compute_period_pnl() -> dict:
    now = datetime.now(timezone.utc)
    today = now.date()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    daily = 0.0
    mtd = 0.0
    ytd = 0.0

    journal = load_json(TRADE_JOURNAL_STATE_PATH, default={}) or {}
    rows = journal.get("rows", []) if isinstance(journal, dict) else []
    if isinstance(rows, list):
        for r in rows:
            if not isinstance(r, dict):
                continue
            dt = _parse_dt(r.get("ts"))
            pnl = safe_float(r.get("realized_pnl", r.get("pnl", 0.0)), 0.0)
            if not dt:
                continue
            if dt.date() == today:
                daily += pnl
            if dt >= month_start:
                mtd += pnl
            if dt >= year_start:
                ytd += pnl

    options_v2 = load_json(OPTIONS_V2_DAILY_REPORT_PATH, default={}) or {}
    perf = options_v2.get("performance", {}) if isinstance(options_v2, dict) else {}
    delta = options_v2.get("delta", {}) if isinstance(options_v2, dict) else {}

    daily += safe_float(delta.get("realized_pnl_delta_eur", 0.0), 0.0)
    daily += safe_float(delta.get("unrealized_pnl_delta_eur", 0.0), 0.0)

    # Options V2 is cumulative since preprod start, so include in MTD/YTD for now.
    options_total = safe_float(perf.get("realized_pnl_eur", 0.0), 0.0) + safe_float(perf.get("unrealized_pnl_eur", 0.0), 0.0)
    mtd += options_total
    ytd += options_total

    options_v3_closed = load_json(OPTIONS_V3_CLOSED_PATH, default=[]) or []
    if isinstance(options_v3_closed, list):
        for r in options_v3_closed:
            if not isinstance(r, dict):
                continue
            dt = _parse_dt(r.get("closed_at"))
            pnl = safe_float(r.get("pnl_eur", 0.0), 0.0)
            if not dt:
                continue
            if dt.date() == today:
                daily += pnl
            if dt >= month_start:
                mtd += pnl
            if dt >= year_start:
                ytd += pnl

    return {
        "pnlDaily": round(daily, 2),
        "pnlMTD": round(mtd, 2),
        "pnlYTD": round(ytd, 2),
    }




def compute_drawdown_from_equity_curve(equity_curve_state: dict) -> dict:
    """
    Compute active portfolio drawdown from the current preprod equity curve.

    Rule:
    - Use active_pnl_eur when available.
    - Fallback to total_pnl_eur.
    - Exclude shadow PnL entirely.
    - Convert PnL into portfolio value using capital_observed_eur.
    """
    try:
        rows = equity_curve_state.get("history", []) if isinstance(equity_curve_state, dict) else []
        if not isinstance(rows, list) or len(rows) < 2:
            return {"drawdown": 0.0, "drawdownValue": 0.0, "drawdownBasis": "active_capital_value"}

        peak = None
        max_dd_pct = 0.0
        max_dd_value = 0.0
        valid_points = 0

        for row in rows:
            if not isinstance(row, dict):
                continue

            capital = safe_float(row.get("capital_observed_eur"), 0.0)
            if capital <= 0:
                continue

            pnl = row.get("active_pnl_eur", row.get("total_pnl_eur"))
            if pnl is None:
                continue

            active_pnl = safe_float(pnl, 0.0)
            value = capital + active_pnl

            if value <= 0:
                continue

            valid_points += 1
            peak = value if peak is None else max(peak, value)

            if peak and peak > 0:
                dd_value = value - peak
                dd_pct = (dd_value / peak) * 100

                if dd_pct < max_dd_pct:
                    max_dd_pct = dd_pct
                    max_dd_value = dd_value

        return {
            "drawdown": round(max_dd_pct, 2),
            "drawdownValue": round(max_dd_value, 2),
            "drawdownBasis": "active_capital_value",
            "drawdownValidPoints": valid_points,
        }
    except Exception:
        return {"drawdown": 0.0, "drawdownValue": 0.0, "drawdownBasis": "active_capital_value"}

def compute_period_delta_from_equity_curve(equity_curve_state: dict, period: str = "day") -> float | None:
    try:
        rows = equity_curve_state.get("history", []) if isinstance(equity_curve_state, dict) else []
        if not isinstance(rows, list) or len(rows) < 2:
            return None

        now = datetime.now(timezone.utc)

        if period == "day":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "year":
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return None

        period_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            dt = _parse_dt(row.get("ts"))
            if dt and dt >= start:
                period_rows.append(row)

        if len(period_rows) < 2:
            return None

        # Use active PnL only. total_pnl_eur is active-only in current schema.
        first = safe_float(period_rows[0].get("total_pnl_eur"), 0.0)
        last = safe_float(period_rows[-1].get("total_pnl_eur"), 0.0)
        return round(last - first, 2)
    except Exception:
        return None


def compute_daily_pnl_from_equity_curve(equity_curve_state: dict) -> float | None:
    try:
        rows = equity_curve_state.get("history", []) if isinstance(equity_curve_state, dict) else []
        if not isinstance(rows, list) or len(rows) < 2:
            return None

        today = datetime.now(timezone.utc).date()
        today_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            dt = _parse_dt(row.get("ts"))
            if dt and dt.date() == today:
                today_rows.append(row)

        if len(today_rows) < 2:
            return None

        # Prefer new schema points where shadow is explicitly separated.
        # This avoids comparing old shadow-included PnL with new active-only PnL.
        active_rows = [
            r for r in today_rows
            if "shadow_pnl_eur" in r or "total_pnl_including_shadow_eur" in r
        ]

        usable_rows = active_rows if len(active_rows) >= 2 else today_rows
        if len(usable_rows) < 2:
            return None

        first = safe_float(usable_rows[0].get("total_pnl_eur"), 0.0)
        last = safe_float(usable_rows[-1].get("total_pnl_eur"), 0.0)
        return round(last - first, 2)
    except Exception:
        return None

def compute_avg_brick_confidence(portfolio_target: dict) -> float:
    confidences = portfolio_target.get("brick_confidence", {}) if isinstance(portfolio_target, dict) else {}
    if not isinstance(confidences, dict) or not confidences:
        return 0.0

    values = []
    for value in confidences.values():
        try:
            values.append(float(value))
        except Exception:
            pass

    if not values:
        return 0.0

    return round(sum(values) / len(values), 6)



def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _extract_crypto_pnl(sim_doc: Any) -> Dict[str, float]:
    realized = 0.0
    unrealized = 0.0

    if isinstance(sim_doc, dict):
        # priorité à un éventuel résumé déjà calculé
        summary_candidates = [
            sim_doc,
            sim_doc.get("summary", {}),
            sim_doc.get("metrics", {}),
            sim_doc.get("portfolio", {}),
            sim_doc.get("performance", {}),
        ]

        for block in summary_candidates:
            if not isinstance(block, dict):
                continue

            r = block.get("realized_pnl_eur", block.get("realizedPnl"))
            u = block.get("unrealized_pnl_eur", block.get("unrealizedPnl"))
            t = block.get("total_pnl_eur", block.get("pnlGlobal", block.get("pnl")))

            if r is not None or u is not None:
                realized = _safe_float(r, 0.0)
                unrealized = _safe_float(u, 0.0)
                return {
                    "realized": round(realized, 2),
                    "unrealized": round(unrealized, 2),
                    "total": round(realized + unrealized, 2),
                }

            if t is not None:
                total = _safe_float(t, 0.0)
                return {
                    "realized": round(total, 2),
                    "unrealized": 0.0,
                    "total": round(total, 2),
                }

        items = (
            sim_doc.get("items")
            or sim_doc.get("trades")
            or sim_doc.get("positions")
            or sim_doc.get("data")
            or []
        )
    elif isinstance(sim_doc, list):
        items = sim_doc
    else:
        items = []

    for item in items:
        if not isinstance(item, dict):
            continue

        status = str(
            item.get("status")
            or item.get("trade_status")
            or item.get("position_status")
            or item.get("state")
            or ""
        ).upper()

        pnl = item.get("pnl_eur", item.get("pnl", item.get("profit_eur", item.get("profit"))))
        realized_raw = item.get("realized_pnl_eur", item.get("realizedPnl"))
        unrealized_raw = item.get("unrealized_pnl_eur", item.get("unrealizedPnl"))

        pnl_val = _safe_float(pnl, 0.0)

        if realized_raw is not None or unrealized_raw is not None:
            realized += _safe_float(realized_raw, 0.0)
            unrealized += _safe_float(unrealized_raw, 0.0)
            continue

        if status in {"OPEN", "ACTIVE", "RUNNING", "HOLD", "SIMULATED"}:
            unrealized += pnl_val
        elif status in {"CLOSED", "SELL", "SOLD", "EXIT", "EXITED", "TAKE_PROFIT", "STOP_LOSS"}:
            realized += pnl_val
        else:
            # fallback prudent : on considère le PnL comme non réalisé si l'état n'est pas exploitable
            unrealized += pnl_val

    return {
        "realized": round(realized, 2),
        "unrealized": round(unrealized, 2),
        "total": round(realized + unrealized, 2),
    }


def load_initial_capital() -> float:
    payload = load_json(INITIAL_CAPITAL_PATH, default={}) or {}
    return safe_float(payload.get("total_capital_eur", 0.0), 0.0)


def _bricks_map(portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(portfolio_state, dict):
        return {}
    bricks = portfolio_state.get("bricks")
    return bricks if isinstance(bricks, dict) else {}


def _target_from_brick(brick: Dict[str, Any], fallback: float = 0.0) -> float:
    if not isinstance(brick, dict):
        return fallback
    return safe_float(
        brick.get("target_weight_snapshot", brick.get("target_weight", brick.get("current_weight_estimate", fallback))),
        fallback,
    )

def _runtime_fields_from_brick(brick: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(brick, dict):
        return {
            "currentExposure": None,
            "currentExposureEur": None,
            "positions": None,
            "stateOrigin": None,
        }

    return {
        "currentExposure": brick.get("current_weight_estimate"),
        "currentExposureEur": brick.get("current_exposure_eur"),
        "positions": brick.get("positions_count"),
        "stateOrigin": brick.get("state_origin"),
    }


def build_crypto_placeholder(portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    bricks = _bricks_map(portfolio_state)
    crypto = bricks.get("crypto", {}) if isinstance(bricks, dict) else {}

    simulation_doc = load_json(CRYPTO_SIMULATION_PATH, default=[]) or []
    if isinstance(simulation_doc, dict):
        sim_items = simulation_doc.get("items", []) or simulation_doc.get("trades", []) or []
    elif isinstance(simulation_doc, list):
        sim_items = simulation_doc
    else:
        sim_items = []

    signal_candidates_doc = load_json(CRYPTO_SIGNAL_CANDIDATES_PATH, default=[]) or []
    if isinstance(signal_candidates_doc, dict):
        signal_candidates_items = signal_candidates_doc.get("items", []) or signal_candidates_doc.get("signals", []) or []
    elif isinstance(signal_candidates_doc, list):
        signal_candidates_items = signal_candidates_doc
    else:
        signal_candidates_items = []

    sim_count = len([x for x in signal_candidates_items if isinstance(x, dict)])

    open_positions_doc = load_json(CRYPTO_OPEN_POSITIONS_PATH, default=[]) or []
    if isinstance(open_positions_doc, list):
        open_positions_count = len([
            x for x in open_positions_doc
            if (
                isinstance(x, dict)
                and x.get("closed") is not True
                and safe_float(x.get("remaining_size", x.get("size", 0.0)), 0.0) > 0
            )
        ])
    else:
        open_positions_count = sim_count

    pnl = _extract_crypto_pnl(simulation_doc)

    # NSC PREPROD CRYPTO REALIZED PNL:
    # Realized exits are owned by pnl_state.json, while open-position mark-to-market
    # remains displayed as unrealized from simulation/open positions.
    pnl_state_doc = load_json(PNL_STATE_PATH, default={}) or {}
    pnl_summary = pnl_state_doc.get("summary", {}) if isinstance(pnl_state_doc, dict) else {}
    realized_from_state = safe_float(pnl_summary.get("realized_pnl_eur"), None)
    unrealized_from_state = safe_float(pnl_summary.get("unrealized_pnl_eur"), None)
    total_from_state = safe_float(pnl_summary.get("total_pnl_eur"), None)

    if realized_from_state is not None and unrealized_from_state is not None and isinstance(pnl, dict):
        pnl = {
            "realized": round(realized_from_state, 2),
            "unrealized": round(unrealized_from_state, 2),
            "total": round(
                total_from_state
                if total_from_state is not None
                else realized_from_state + unrealized_from_state,
                2,
            ),
        }

    # NSC PREPROD PNL CONSISTENCY:
    # If crypto has no active open position, simulation PnL must not be displayed as unrealized.
    # It remains part of active performance, but is classified as realized/closed simulation PnL.
    if open_positions_count == 0 and isinstance(pnl, dict):
        total_pnl = safe_float(pnl.get("total"), 0.0)
        pnl = {
            "realized": round(total_pnl, 2),
            "unrealized": 0.0,
            "total": round(total_pnl, 2),
        }

    execution_plan_doc = load_json(CRYPTO_EXECUTION_PLAN_PATH, default={}) or {}
    execution_orders = execution_plan_doc.get("orders", []) if isinstance(execution_plan_doc, dict) else []
    if not isinstance(execution_orders, list):
        execution_orders = []
    crypto_orders_count = len([x for x in execution_orders if isinstance(x, dict)])

    return {
        "key": "crypto",
        "name": "Crypto",
        "status": "PREPROD",
        "env": "PREPROD",
        "mode": "SIMULATED_ONLY",
        "candidates": sim_count,
        "orders": crypto_orders_count,
        "openPositions": open_positions_count,
        "pnl": pnl["total"],
        "realizedPnl": pnl["realized"],
        "unrealizedPnl": pnl["unrealized"],
        "limitsOk": True,
        "softVetos": [],
        "source": str(CRYPTO_OPEN_POSITIONS_PATH),
        "note": "Crypto candidates are displayed from signal_candidates.json; open positions are displayed from open_positions.json.",
        "targetExposure": crypto.get("target_weight_snapshot", crypto.get("target_weight", crypto.get("current_weight_estimate", 0.10))),
        "confidence": crypto.get("confidence", 0.0),
        "regime": crypto.get("regime", "neutral"),
        **_runtime_fields_from_brick(crypto),
    }


def build_equities_strategy(portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    bundle = load_json(EQUITIES_UI_BUNDLE, default={}) or {}
    kpis = bundle.get("kpis") if isinstance(bundle, dict) else {}
    if not isinstance(kpis, dict):
        kpis = {}

    protection = bundle.get("protection") if isinstance(bundle, dict) else {}
    if not isinstance(protection, dict):
        protection = {}

    protected_positions = protection.get("protected_positions", [])
    if not isinstance(protected_positions, list):
        protected_positions = []

    protection_statuses = [
        p.get("protection_status")
        for p in protected_positions
        if isinstance(p, dict) and p.get("protection_status")
    ]

    exposure = bundle.get("exposure") if isinstance(bundle, dict) else {}
    if not isinstance(exposure, dict):
        exposure = {}

    equity_curve = load_json(OFFENSIVE_EQUITY_CURVE_PATH, default={}) or {}
    breakdown = equity_curve.get("breakdown", {}) if isinstance(equity_curve, dict) else {}
    if not isinstance(breakdown, dict):
        breakdown = {}

    realized_pnl = safe_float(breakdown.get("realized_pnl", 0.0), 0.0)
    unrealized_pnl = safe_float(breakdown.get("unrealized_pnl", 0.0), 0.0)
    total_pnl = round(realized_pnl + unrealized_pnl, 2)

    bricks = _bricks_map(portfolio_state)
    offensive = bricks.get("equities_offensive", {}) if isinstance(bricks, dict) else {}

    return {
        "key": "equities_offensive",
        "name": "Actions Offensives",
        "status": "PREPROD",
        "env": "PREPROD",
        "mode": kpis.get("action_policy", "SIMULATED_ONLY"),
        "candidates": int(kpis.get("signals_count", kpis.get("candidates_count", 0)) or 0),
        "orders": int(kpis.get("execution_orders_final", kpis.get("orders_count", 0)) or 0),
        "openPositions": int(kpis.get("open_positions", 0) or 0),
        "pnl": total_pnl,
        "realizedPnl": round(realized_pnl, 2),
        "unrealizedPnl": round(unrealized_pnl, 2),
        "limitsOk": kpis.get("limits_ok", True),
        "softVetos": kpis.get("soft_vetos", []) or [],
        "source": str(EQUITIES_UI_BUNDLE),
        "regime": offensive.get("regime", kpis.get("market_regime", "UNKNOWN")),
        "regimeConfidence": safe_float(offensive.get("confidence", kpis.get("market_confidence", 0.0)), 0.0),
        "planId": kpis.get("plan_id"),
        "targetExposure": _target_from_brick(offensive, 0.15),
        "confidence": safe_float(offensive.get("confidence", kpis.get("market_confidence", 0.0)), 0.0),
        "protectedPositionsCount": int(kpis.get("protected_positions_count", 0) or 0),
        "trailingHitCount": int(kpis.get("trailing_hit_count", 0) or 0),
        "portfolioRegimeOffensive": exposure.get("portfolio_regime", kpis.get("regime")),
        "protectionStatuses": protection_statuses,
        "protectionDetail": protected_positions,
        "totalNotionalUsd": safe_float(exposure.get("total_notional_usd", 0.0), 0.0),
        **_runtime_fields_from_brick(offensive),
    }

def build_defensive_strategy(portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    state = load_json(DEFENSIVE_STATE_PATH, default={}) or {}
    signal = load_json(DEFENSIVE_SIGNAL_PATH, default={}) or {}
    bricks = _bricks_map(portfolio_state)
    defensive = bricks.get("equities_defensive", {}) if isinstance(bricks, dict) else {}
    score_summary = signal.get("score_summary", {}) if isinstance(signal, dict) else {}

    positions = state.get("positions", []) if isinstance(state, dict) else []
    if not isinstance(positions, list):
        positions = []

    open_positions = len([p for p in positions if safe_float(p.get("qty", 0.0), 0.0) > 0])
    realized = safe_float(state.get("realized_pnl_eur", 0.0), 0.0)
    unrealized = safe_float(state.get("unrealized_pnl_eur", 0.0), 0.0)
    total_pnl = safe_float(state.get("pnl_eur", realized + unrealized), 0.0)

    return {
        "key": "equities_defensive",
        "name": "Actions Défensives",
        "status": "PREPROD",
        "env": "PREPROD",
        "mode": "SIMULATED_EXECUTION",
        "candidates": int(score_summary.get("selected_assets_count", len(positions)) or len(positions)),
        "orders": 0,
        "openPositions": open_positions,
        "pnl": round(total_pnl, 2),
        "realizedPnl": round(realized, 2),
        "unrealizedPnl": round(unrealized, 2),
        "limitsOk": bool(score_summary.get("constraints_respected", True)),
        "softVetos": [],
        "source": str(DEFENSIVE_STATE_PATH if state else DEFENSIVE_SIGNAL_PATH),
        "targetExposure": _target_from_brick(defensive, safe_float(state.get("target_exposure", signal.get("target_exposure", 0.20)), 0.20)),
        "confidence": safe_float(defensive.get("confidence", state.get("confidence", signal.get("confidence", 0.0))), 0.0),
        "regime": defensive.get("regime", state.get("regime", "stabilization_active")),
        "portfolioBeta": score_summary.get("portfolio_beta_estimate"),
        "averageScore": score_summary.get("average_defensive_score"),
        "reason": signal.get("reason"),
        "totalNotionalEur": safe_float(state.get("current_exposure_eur", 0.0), 0.0),
        **_runtime_fields_from_brick(defensive),
    }


def build_long_term_strategy(portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    bricks = _bricks_map(portfolio_state)
    long_term = bricks.get("long_term", {}) if isinstance(bricks, dict) else {}

    lt_path = Path("/opt/nsc/app/data/portfolio/lt_portfolio_valuation.json")
    lt = load_json(lt_path, default={}) or {}
    totals = lt.get("totals", {}) if isinstance(lt, dict) else {}
    positions_raw = lt.get("positions", []) if isinstance(lt, dict) else []
    positions = list(positions_raw.values()) if isinstance(positions_raw, dict) else positions_raw

    market_value = safe_float(totals.get("market_value_eur"), 0.0)
    cost_basis = safe_float(totals.get("cost_basis_eur", totals.get("invested_eur")), 0.0)
    unrealized = safe_float(totals.get("unrealized_pnl_eur", totals.get("pnl_eur")), 0.0)
    pnl_pct = safe_float(totals.get("unrealized_pnl_pct", totals.get("pnl_pct")), 0.0)

    return {
        "key": "long_term",
        "name": "Long Term",
        "status": "PREPROD",
        "env": "PREPROD",
        "mode": "PATRIMONIAL",
        "candidates": 0,
        "orders": 0,
        "openPositions": len(positions) if isinstance(positions, list) else 0,
        "pnl": round(unrealized, 2),
        "realizedPnl": 0.0,
        "unrealizedPnl": round(unrealized, 2),
        "pnlPct": round(pnl_pct * 100, 2),
        "marketValueEur": round(market_value, 2),
        "costBasisEur": round(cost_basis, 2),
        "limitsOk": True,
        "softVetos": [],
        "source": str(lt_path),
        "targetExposure": _target_from_brick(long_term, 0.0),
        "currentExposure": safe_float(long_term.get("current_weight_estimate"), 0.0),
        "currentExposureEur": market_value,
        "confidence": safe_float(long_term.get("confidence", 0.0), 0.0),
        "regime": long_term.get("regime", "patrimonial"),
        "positions": len(positions) if isinstance(positions, list) else 0,
        "stateOrigin": "lt_portfolio_valuation",
    }


def build_bonds_strategy(portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    state = load_json(BONDS_STATE_PATH, default={}) or {}
    signal = load_json(BONDS_SIGNAL_PATH, default={}) or {}
    bricks = _bricks_map(portfolio_state)
    bonds = bricks.get("bonds", {}) if isinstance(bricks, dict) else {}

    positions = state.get("positions", []) if isinstance(state, dict) else []
    if not isinstance(positions, list):
        positions = []

    deployed = bool(state or signal)
    open_positions = len([p for p in positions if safe_float(p.get("qty", 0.0), 0.0) > 0])
    realized = safe_float(state.get("realized_pnl_eur", 0.0), 0.0)
    unrealized = safe_float(state.get("unrealized_pnl_eur", 0.0), 0.0)
    total_pnl = safe_float(state.get("pnl_eur", realized + unrealized), 0.0)

    return {
        "key": "bonds",
        "name": "Obligations",
        "status": "PREPROD" if deployed else "NOT_DEPLOYED",
        "env": "PREPROD" if deployed else "N/A",
        "mode": "SIMULATED_EXECUTION" if deployed else "N/A",
        "candidates": len(positions),
        "orders": 0,
        "openPositions": open_positions,
        "pnl": round(total_pnl, 2),
        "realizedPnl": round(realized, 2),
        "unrealizedPnl": round(unrealized, 2),
        "limitsOk": True,
        "softVetos": [],
        "source": str(BONDS_STATE_PATH if state else BONDS_SIGNAL_PATH),
        "targetExposure": _target_from_brick(bonds, safe_float(state.get("target_exposure", signal.get("target_exposure", 0.0)), 0.0)),
        "confidence": safe_float(bonds.get("confidence", state.get("confidence", signal.get("confidence", 0.0))), 0.0),
        "regime": bonds.get("regime", state.get("regime", "neutral_defensive")),
        "totalNotionalEur": safe_float(state.get("current_exposure_eur", 0.0), 0.0),
        **_runtime_fields_from_brick(bonds),
    }


def build_metals_strategy(portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    state = load_json(METALS_STATE_PATH, default={}) or {}
    signal = load_json(METALS_SIGNAL_PATH, default={}) or {}
    bricks = _bricks_map(portfolio_state)
    metals = bricks.get("precious_metals", {}) if isinstance(bricks, dict) else {}

    positions = state.get("positions", []) if isinstance(state, dict) else []
    if not isinstance(positions, list):
        positions = []

    deployed = bool(state or signal)
    open_positions = len([p for p in positions if safe_float(p.get("qty", 0.0), 0.0) > 0])
    realized = safe_float(state.get("realized_pnl_eur", 0.0), 0.0)
    unrealized = safe_float(state.get("unrealized_pnl_eur", 0.0), 0.0)
    total_pnl = safe_float(state.get("pnl_eur", realized + unrealized), 0.0)

    return {
        "key": "metals",
        "name": "Métaux Précieux",
        "status": "PREPROD" if deployed else "NOT_DEPLOYED",
        "env": "PREPROD" if deployed else "N/A",
        "mode": "SIMULATED_EXECUTION" if deployed else "N/A",
        "candidates": len(positions),
        "orders": 0,
        "openPositions": open_positions,
        "pnl": round(total_pnl, 2),
        "realizedPnl": round(realized, 2),
        "unrealizedPnl": round(unrealized, 2),
        "limitsOk": True,
        "softVetos": [],
        "source": str(METALS_STATE_PATH if state else METALS_SIGNAL_PATH),
        "targetExposure": _target_from_brick(metals, safe_float(state.get("target_exposure", signal.get("target_exposure", 0.0)), 0.0)),
        "confidence": safe_float(metals.get("confidence", state.get("confidence", signal.get("confidence", 0.0))), 0.0),
        "regime": metals.get("regime", state.get("regime", "systemic_hedge_active")),
        "totalNotionalEur": safe_float(state.get("current_exposure_eur", 0.0), 0.0),
        **_runtime_fields_from_brick(metals),
    }




def build_options_v3_shadow_strategy(portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    dashboard = load_options_v3_dashboard() or {}

    status = dashboard.get("status", {}) if isinstance(dashboard, dict) else {}
    kpis = dashboard.get("kpis", {}) if isinstance(dashboard, dict) else {}
    portfolio = dashboard.get("portfolio", {}) if isinstance(dashboard, dict) else {}
    positions = dashboard.get("positions", {}) if isinstance(dashboard, dict) else {}

    return {
        "key": "options_v3_shadow",
        "name": "Options V3 Shadow",
        "strategy": "options_v3_shadow",
        "label": "Options V3 Shadow",
        "mode": "SHADOW",
        "regime": "shadow_mode",
        "targetExposure": 0.0,
        "openPositions": int(positions.get("open", 0) or 0),
        "orders": int(kpis.get("approved_count", 0) or 0),
        "pnl": 0.0,
        "winRate": float(
            dashboard.get("comparison_reference", {}).get("v2_win_rate_pct", 0) or 0
        ),
        "shadowComparisonPnL": float(
            dashboard.get("comparison_reference", {}).get("v2_realized_pnl_eur", 0) or 0
        ),
        "signalsValidated": int(kpis.get("candidates_validated", 0) or 0),
        "signalsRejected": int(kpis.get("rejected_count", 0) or 0),
        "pipelineStatus": status.get("pipeline_status", "unknown"),
        "source": str(OPTIONS_V3_PATH / "options_v3_dashboard.json"),
        "currentExposure": 0.0,
        "currentExposureEur": 0.0,
        "positions": int(positions.get("open", 0) or 0),
        "stateOrigin": "options_v3_shadow_dashboard",
    }



def build_options_us_strategy(
    portfolio_state: Dict[str, Any],
) -> Dict[str, Any]:
    bricks = _bricks_map(portfolio_state)

    options_state = (
        bricks.get("options_us", {})
        if isinstance(bricks, dict)
        else {}
    )

    if not isinstance(options_state, dict):
        options_state = {}

    risk_flags = options_state.get("risk_flags", {}) or {}
    allocation = options_state.get("allocation", {}) or {}

    governed_target = (
        options_state.get("governed_target") is True
    )

    target_weight = safe_float(
        options_state.get("target_weight_snapshot", 0.0),
        0.0,
    )

    raw_weight = safe_float(
        options_state.get("raw_signal_weight", 0.0),
        0.0,
    )

    current_weight = safe_float(
        options_state.get("current_weight_estimate", 0.0),
        0.0,
    )

    target_amount_eur = safe_float(
        options_state.get("target_amount_eur", 0.0),
        0.0,
    )

    current_exposure_eur = safe_float(
        options_state.get("current_exposure_eur", 0.0),
        0.0,
    )

    realized_pnl = safe_float(
        risk_flags.get("realized_pnl_eur", 0.0),
        0.0,
    )

    unrealized_pnl = safe_float(
        risk_flags.get("unrealized_pnl_eur", 0.0),
        0.0,
    )

    total_pnl = round(
        realized_pnl + unrealized_pnl,
        2,
    )

    execution_blocked = (
        risk_flags.get("execution_blocked") is True
    )

    real_money_disabled = (
        risk_flags.get("real_money_disabled") is True
    )

    safety_contract_ok = (
        risk_flags.get("safety_contract_ok") is True
    )

    pipeline_healthy = (
        risk_flags.get("pipeline_healthy") is True
    )

    runtime_mode = str(
        options_state.get("status")
        or options_state.get("regime")
        or ""
    ).upper()

    if governed_target and execution_blocked:
        display_mode = "ACTIVE_SIMULATED"
    elif governed_target:
        display_mode = "ACTIVE"
    else:
        display_mode = "UNAVAILABLE"

    status = str(
        options_state.get("status")
        or "UNAVAILABLE"
    ).upper()

    policy_exclusion_reason = (
        options_state.get("policy_exclusion_reason")
    )

    soft_vetos = []

    if execution_blocked:
        soft_vetos.append("real_execution_blocked")

    if real_money_disabled:
        soft_vetos.append("real_money_disabled")

    if policy_exclusion_reason:
        soft_vetos.append(
            str(policy_exclusion_reason)
        )

    return {
        "key": "options_us",
        "name": "Options US",
        "strategy": "options_us",
        "label": "Options US",
        "status": status,
        "env": "PREPROD",
        "mode": display_mode,
        "runtimeMode": runtime_mode or None,
        "governedTarget": governed_target,
        "policyExclusionReason": policy_exclusion_reason,
        "candidates": 0,
        "orders": 0,
        "openPositions": int(
            options_state.get("positions_count", 0)
            or 0
        ),
        "positions": int(
            options_state.get("positions_count", 0)
            or 0
        ),
        "pnl": total_pnl,
        "realizedPnl": realized_pnl,
        "unrealizedPnl": unrealized_pnl,
        "limitsOk": safety_contract_ok,
        "softVetos": soft_vetos,
        "source": options_state.get("state_source"),
        "stateOrigin": options_state.get("state_origin"),
        "portfolioRole": options_state.get("portfolio_role"),
        "fundingPool": options_state.get("funding_pool"),
        "regime": options_state.get("regime"),
        "confidence": safe_float(
            options_state.get("confidence", 0.0),
            0.0,
        ),
        "rawTargetExposure": raw_weight,
        "targetExposure": target_weight,
        "targetAmountEur": target_amount_eur,
        "currentExposure": current_weight,
        "currentExposureEur": current_exposure_eur,
        "executionBlocked": execution_blocked,
        "realMoneyDisabled": real_money_disabled,
        "safetyContractOk": safety_contract_ok,
        "pipelineHealthy": pipeline_healthy,
        "estimatedRiskOpenEur": safe_float(
            risk_flags.get(
                "estimated_risk_open_eur",
                allocation.get(
                    "internal_used_risk_eur",
                    0.0,
                ),
            ),
            0.0,
        ),
        "usedRiskPct": safe_float(
            risk_flags.get(
                "used_risk_pct",
                allocation.get(
                    "internal_used_risk_pct",
                    0.0,
                ),
            ),
            0.0,
        ),
        "statusDetail": (
            "Governed Options US allocation in simulated-only mode."
            if governed_target
            else "Options US governed allocation unavailable."
        ),
    }



def build_recent_activity() -> List[Dict[str, Any]]:
    trades = load_json(OPTIONS_V2_TRADES_PATH, default=[]) or []
    if not isinstance(trades, list):
        return []

    activity: List[Dict[str, Any]] = []
    for item in reversed(trades[-8:]):
        if not isinstance(item, dict):
            continue
        activity.append({
            "ts": item.get("ts"),
            "brick": "Options US",
            "type": item.get("action", "TRADE"),
            "symbol": item.get("ticker", "N/A"),
            "strategy": item.get("strategy", "N/A"),
            "pnl_eur": safe_float(item.get("pnl_eur", 0.0), 0.0),
            "status": item.get("status", "ok"),
        })
    return activity




def read_confidence_history() -> dict:
    try:
        if not CONFIDENCE_HISTORY_PATH.exists():
            return {"status": "missing", "latest": None, "previous": None, "delta": None, "history_len": 0}

        rows = []
        for line in CONFIDENCE_HISTORY_PATH.read_text(encoding="utf-8").splitlines()[-200:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass

        if not rows:
            return {"status": "empty", "latest": None, "previous": None, "delta": None, "history_len": 0}

        latest_row = rows[-1]
        latest = latest_row.get("confidence_value", latest_row.get("confidence"))

        previous = None
        if len(rows) >= 2:
            prev_row = rows[-2]
            previous = prev_row.get("confidence_value", prev_row.get("confidence"))

        delta = None
        if latest is not None and previous is not None:
            delta = round(float(latest) - float(previous), 6)

        return {
            "status": "online",
            "latest": latest_row,
            "previous": previous,
            "delta": delta,
            "history_len": len(rows),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "latest": None, "previous": None, "delta": None, "history_len": 0}

@router.get("/dashboard/v3")
def dashboard_v3() -> Dict[str, Any]:
    portfolio_state = load_json(PORTFOLIO_STATE_PATH, default={}) or {}
    portfolio_target = load_json(PORTFOLIO_TARGET_PATH, default={}) or {}
    equity_curve_state = load_json(EQUITY_CURVE_STATE_PATH, default={}) or {}

    crypto = build_crypto_placeholder(portfolio_state)
    equities = build_equities_strategy(portfolio_state)
    defensive = build_defensive_strategy(portfolio_state)
    long_term = build_long_term_strategy(portfolio_state)
    options_us = build_options_us_strategy(portfolio_state)
    options_v3_shadow = build_options_v3_shadow_strategy(portfolio_state)
    bonds = build_bonds_strategy(portfolio_state)
    metals = build_metals_strategy(portfolio_state)

    strategies = [
        crypto,
        equities,
        defensive,
        long_term,
        options_us,
        options_v3_shadow,
        bonds,
        metals,
    ]

    avg_brick_confidence = compute_avg_brick_confidence(portfolio_target)
    confidence_history = read_confidence_history()

    pnl_shadow = round(sum(
        safe_float(s.get("pnl", 0.0), 0.0)
        for s in strategies
        if s.get("key") in {"options_v2_shadow", "options_v3_shadow"}
    ), 2)

    pnl_long_term = round(sum(
        safe_float(s.get("pnl", 0.0), 0.0)
        for s in strategies
        if s.get("key") in {"long_term"}
    ), 2)

    pnl_global = round(sum(
        safe_float(s.get("pnl", 0.0), 0.0)
        for s in strategies
        if s.get("key") not in {"options_v2_shadow", "options_v3_shadow", "long_term"}
    ), 2)

    pnl_total_including_shadow = round(pnl_global + pnl_shadow, 2)
    pnl_total_including_long_term = round(pnl_global + pnl_long_term, 2)
    pnl_total_including_long_term_and_shadow = round(pnl_global + pnl_long_term + pnl_shadow, 2)

    protected_bricks = 0
    trailing_hits = 0
    protection_summary = []

    for s in strategies:
        protected_count = int(s.get("protectedPositionsCount", 0) or 0)
        trailing_count = int(s.get("trailingHitCount", 0) or 0)

        if protected_count > 0:
            protected_bricks += 1
        if trailing_count > 0:
            trailing_hits += trailing_count

        if protected_count > 0 or trailing_count > 0:
            protection_summary.append({
                "brick": s.get("key"),
                "protectedPositionsCount": protected_count,
                "trailingHitCount": trailing_count,
                "protectionStatuses": s.get("protectionStatuses", []) or [],
            })

    protection_level = "UNPROTECTED"
    if trailing_hits > 0:
        protection_level = "ALERT"
    elif protected_bricks > 0:
        protection_level = "PROTECTED"

    master_audit = load_json(MASTER_COHERENCE_AUDIT_PATH, default={}) or {}
    global_audit = load_json(GLOBAL_ORCHESTRATION_AUDIT_PATH, default={}) or {}
    supervision_gate = load_json(SUPERVISION_GATE_PATH, default={}) or {}
    institutional_summary = load_json(INSTITUTIONAL_SUPERVISION_SUMMARY_PATH, default={}) or {}
    stress_tests = load_json(GLOBAL_PREPROD_STRESS_TESTS_PATH, default={}) or {}
    preprod_history = load_json(GLOBAL_PREPROD_HISTORY_SUMMARY_PATH, default={}) or {}
    preprod_trend = load_json(GLOBAL_PREPROD_TREND_MONITOR_PATH, default={}) or {}
    preprod_anomaly = load_json(GLOBAL_PREPROD_ANOMALY_DETECTOR_PATH, default={}) or {}
    preprod_readiness = load_json(GLOBAL_PREPROD_LONG_RUN_READINESS_PATH, default={}) or {}
    long_run_daily_report = load_json(GLOBAL_PREPROD_LONG_RUN_DAILY_REPORT_PATH, default={}) or {}
    preprod_shadow = load_json(GLOBAL_PREPROD_48H_SHADOW_SUPERVISOR_PATH, default={}) or {}
    master_summary = master_audit.get("summary", {}) if isinstance(master_audit, dict) else {}

    rebalance_plan = load_json(MASTER_REBALANCE_PLAN_PATH, default={}) or {}
    rebalance_summary = rebalance_plan.get("summary", {}) if isinstance(rebalance_plan, dict) else {}

    funding_plan = load_json(MASTER_FUNDING_PLAN_PATH, default={}) or {}
    funding_pools = funding_plan.get("funding_pools", []) if isinstance(funding_plan, dict) else []

    funding_by_pool = {
        p.get("pool"): {
            "netRequiredEur": p.get("net_required_eur", 0.0),
            "itemsCount": len(p.get("items") or []),
            "manualTransferRequired": bool(p.get("manual_transfer_required", False)),
        }
        for p in funding_pools
        if isinstance(p, dict) and p.get("pool")
    }


    def _mtime(path):
        try:
            return path.stat().st_mtime
        except Exception:
            return None

    master_stale_missing = []
    master_stale_items = []

    master_stale_paths = {
        "open_positions": CRYPTO_OPEN_POSITIONS_PATH,
        "portfolio_state": PORTFOLIO_STATE_PATH,
        "rebalance_plan": MASTER_REBALANCE_PLAN_PATH,
        "funding_plan": MASTER_FUNDING_PLAN_PATH,
        "master_audit": MASTER_COHERENCE_AUDIT_PATH,
    }

    master_stale_mtimes = {k: _mtime(v) for k, v in master_stale_paths.items()}
    master_stale_missing = [k for k, v in master_stale_mtimes.items() if v is None]

    open_positions_mtime = master_stale_mtimes.get("open_positions")
    if open_positions_mtime:
        for key in ["portfolio_state", "rebalance_plan", "funding_plan", "master_audit"]:
            artifact_mtime = master_stale_mtimes.get(key)
            if artifact_mtime is None:
                master_stale_items.append(f"{key}:missing")
            elif artifact_mtime + 2 < open_positions_mtime:
                master_stale_items.append(f"{key}:older_than_open_positions")

    master_stale_status = "BLOCKING" if master_stale_missing or master_stale_items else "OK"

    master_errors = int(master_summary.get("errors_count", 0) or 0)
    master_warnings = int(master_summary.get("warnings_count", 0) or 0)
    master_missing = master_summary.get("missing_artifacts") or []
    master_guardrail_status = "BLOCKING" if (master_errors > 0 or len(master_missing) > 0) else ("WARNING" if master_warnings > 0 else "OK")

    orchestration_status = "OK"
    orchestration_reasons = []

    if master_guardrail_status == "BLOCKING":
        orchestration_status = "BLOCKING"
        orchestration_reasons.append("master_guardrail_blocking")

    if master_stale_status == "BLOCKING":
        orchestration_status = "BLOCKING"
        orchestration_reasons.append("master_stale_blocking")

    if isinstance(rebalance_plan, dict) and rebalance_plan.get("status") != "ok":
        orchestration_status = "BLOCKING"
        orchestration_reasons.append("rebalance_plan_not_ok")

    if isinstance(funding_plan, dict) and funding_plan.get("status") != "ok":
        orchestration_status = "BLOCKING"
        orchestration_reasons.append("funding_plan_not_ok")

    if orchestration_status != "BLOCKING" and master_warnings > 0:
        orchestration_status = "WARNING"
        orchestration_reasons.append("master_audit_warnings")

    if not orchestration_reasons:
        orchestration_reasons.append("all_master_checks_ok")

    period_pnl = compute_period_pnl()
    drawdown_metrics = compute_drawdown_from_equity_curve(equity_curve_state)
    equity_daily_pnl = compute_period_delta_from_equity_curve(equity_curve_state, "day")
    equity_mtd_pnl = compute_period_delta_from_equity_curve(equity_curve_state, "month")
    equity_ytd_pnl = compute_period_delta_from_equity_curve(equity_curve_state, "year")

    preprod_safe_nominal = (
        isinstance(institutional_summary, dict)
        and institutional_summary.get("preprod_safe_nominal") is True
    )

    effective_global_status = (
        institutional_summary.get("global_status")
        if preprod_safe_nominal
        else global_audit.get("global_status") if isinstance(global_audit, dict) else None
    )

    effective_global_alert_level = (
        institutional_summary.get("alert_level")
        if preprod_safe_nominal
        else global_audit.get("alert_level") if isinstance(global_audit, dict) else None
    )

    effective_global_blocking = (
        institutional_summary.get("blocking")
        if preprod_safe_nominal
        else global_audit.get("blocking") if isinstance(global_audit, dict) else None
    )

    effective_global_summary = (
        institutional_summary.get("audit")
        if preprod_safe_nominal
        else global_audit.get("summary") if isinstance(global_audit, dict) else None
    )

    effective_global_domains = (
        institutional_summary.get("domains")
        if preprod_safe_nominal
        else global_audit.get("domains") if isinstance(global_audit, dict) else None
    )


    operational_confidence = load_json(OPERATIONAL_CONFIDENCE_PATH, default={}) or {}
    execution_confidence = load_json(EXECUTION_CONFIDENCE_PATH, default={}) or {}

    global_payload = {
        "env": "PREPROD",
        "regime": portfolio_target.get("portfolio_regime", "unknown"),
        "confidence": avg_brick_confidence,
        "confidencePct": round(avg_brick_confidence * 100, 2),
        "strategicConfidence": avg_brick_confidence,
        "strategicConfidencePct": round(avg_brick_confidence * 100, 2),
        "operationalConfidence": safe_float(operational_confidence.get("confidence"), 0.0),
        "operationalConfidencePct": safe_float(operational_confidence.get("confidencePct"), 0.0),
        "executionConfidence": safe_float(execution_confidence.get("confidence"), 0.0),
        "executionConfidencePct": safe_float(execution_confidence.get("confidencePct"), 0.0),
        "confidenceSplit": {
            "strategic": {
                "label": "Strategic",
                "confidence": avg_brick_confidence,
                "confidencePct": round(avg_brick_confidence * 100, 2),
                "source": str(PORTFOLIO_TARGET_PATH),
            },
            "operational": {
                "label": "Operational",
                "confidence": safe_float(operational_confidence.get("confidence"), 0.0),
                "confidencePct": safe_float(operational_confidence.get("confidencePct"), 0.0),
                "source": str(OPERATIONAL_CONFIDENCE_PATH),
            },
            "execution": {
                "label": "Execution",
                "confidence": safe_float(execution_confidence.get("confidence"), 0.0),
                "confidencePct": safe_float(execution_confidence.get("confidencePct"), 0.0),
                "source": str(EXECUTION_CONFIDENCE_PATH),
            },
        },
        "confidenceHistory": confidence_history,
        "confidenceDelta": confidence_history.get("delta") if isinstance(confidence_history, dict) else None,
        "confidenceStatus": confidence_history.get("status") if isinstance(confidence_history, dict) else "unknown",
        "confidenceHistory": confidence_history,
        "confidenceDelta": confidence_history.get("delta") if isinstance(confidence_history, dict) else None,
        "confidenceStatus": confidence_history.get("status") if isinstance(confidence_history, dict) else "unknown",
        "orchestrationStatus": orchestration_status,
        "orchestrationReasons": orchestration_reasons,
        "globalAuditStatus": effective_global_status,
        "globalAuditAlertLevel": effective_global_alert_level,
        "globalAuditBlocking": effective_global_blocking,
        "globalAuditSummary": effective_global_summary,
        "globalAuditDomains": effective_global_domains,
        "globalAuditRawStatus": global_audit.get("global_status") if isinstance(global_audit, dict) else None,
        "globalAuditRawBlocking": global_audit.get("blocking") if isinstance(global_audit, dict) else None,
        "supervisionGateOpen": supervision_gate.get("gate_open") if isinstance(supervision_gate, dict) else None,
        "supervisionGateMode": supervision_gate.get("mode") if isinstance(supervision_gate, dict) else None,
        "supervisionGateActions": supervision_gate.get("recommended_actions") if isinstance(supervision_gate, dict) else None,
        "institutionalLayerReady": institutional_summary.get("institutional_layer_ready") if isinstance(institutional_summary, dict) else None,
        "institutionalSummaryStatus": institutional_summary.get("global_status") if isinstance(institutional_summary, dict) else None,
        "institutionalSummaryAudit": institutional_summary.get("audit") if isinstance(institutional_summary, dict) else None,
        "institutionalSummaryGate": institutional_summary.get("gate") if isinstance(institutional_summary, dict) else None,
        "globalPreprodStressTests": {
            "status": stress_tests.get("status") if isinstance(stress_tests, dict) else None,
            "mode": stress_tests.get("mode") if isinstance(stress_tests, dict) else None,
            "summary": stress_tests.get("summary") if isinstance(stress_tests, dict) else None,
            "failed_scenarios": stress_tests.get("failed_scenarios") if isinstance(stress_tests, dict) else None,
        },
        "globalPreprodHistorySummary": {
            "status": preprod_history.get("status") if isinstance(preprod_history, dict) else None,
            "summary": preprod_history.get("summary") if isinstance(preprod_history, dict) else None,
            "last_run": preprod_history.get("last_run") if isinstance(preprod_history, dict) else None,
        },
        "globalPreprodTrendMonitor": {
            "trend_status": preprod_trend.get("trend_status") if isinstance(preprod_trend, dict) else None,
            "metrics": preprod_trend.get("metrics") if isinstance(preprod_trend, dict) else None,
            "last_run": preprod_trend.get("last_run") if isinstance(preprod_trend, dict) else None,
            "alerts": preprod_trend.get("alerts") if isinstance(preprod_trend, dict) else None,
        },
        "globalPreprodAnomalyDetector": {
            "anomaly_status": preprod_anomaly.get("anomaly_status") if isinstance(preprod_anomaly, dict) else None,
            "summary": preprod_anomaly.get("summary") if isinstance(preprod_anomaly, dict) else None,
            "inputs": preprod_anomaly.get("inputs") if isinstance(preprod_anomaly, dict) else None,
            "anomalies": preprod_anomaly.get("anomalies") if isinstance(preprod_anomaly, dict) else None,
        },
        "globalPreprodLongRunReadiness": {
            "readiness_status": preprod_readiness.get("readiness_status") if isinstance(preprod_readiness, dict) else None,
            "summary": preprod_readiness.get("summary") if isinstance(preprod_readiness, dict) else None,
            "failed_checks": preprod_readiness.get("failed_checks") if isinstance(preprod_readiness, dict) else None,
            "decision": preprod_readiness.get("decision") if isinstance(preprod_readiness, dict) else None,
        },
        "globalPreprodLongRunDailyReport": {
            "status": long_run_daily_report.get("status") if isinstance(long_run_daily_report, dict) else None,
            "generated_at": long_run_daily_report.get("generated_at") if isinstance(long_run_daily_report, dict) else None,
            "session": long_run_daily_report.get("session") if isinstance(long_run_daily_report, dict) else None,
            "progress": long_run_daily_report.get("progress") if isinstance(long_run_daily_report, dict) else None,
            "headline": long_run_daily_report.get("headline") if isinstance(long_run_daily_report, dict) else None,
            "kpis": long_run_daily_report.get("kpis") if isinstance(long_run_daily_report, dict) else None,
            "decision": long_run_daily_report.get("decision") if isinstance(long_run_daily_report, dict) else None,
        },
        "globalPreprod48hShadowSupervisor": {
            "shadow_status": preprod_shadow.get("shadow_status") if isinstance(preprod_shadow, dict) else None,
            "progress": preprod_shadow.get("progress") if isinstance(preprod_shadow, dict) else None,
            "summary": preprod_shadow.get("summary") if isinstance(preprod_shadow, dict) else None,
            "failed_checks": preprod_shadow.get("failed_checks") if isinstance(preprod_shadow, dict) else None,
            "runtime": preprod_shadow.get("runtime") if isinstance(preprod_shadow, dict) else None,
            "decision": preprod_shadow.get("decision") if isinstance(preprod_shadow, dict) else None,
        },
        "masterGuardrailStatus": master_guardrail_status,
        "masterStaleStatus": master_stale_status,
        "masterStaleMissing": master_stale_missing,
        "masterStaleItems": master_stale_items,
        "masterAuditStatus": master_audit.get("status", "unknown") if isinstance(master_audit, dict) else "unknown",
        "masterAuditErrors": int(master_summary.get("errors_count", 0) or 0),
        "masterAuditWarnings": int(master_summary.get("warnings_count", 0) or 0),
        "masterAuditTotalWithCash": master_summary.get("total_with_cash"),
        "masterAuditGovernancePolicy": master_summary.get("governance_action_policy"),
        "masterAuditHardBlock": bool(master_summary.get("governance_hard_block", False)),
        "masterRebalanceStatus": rebalance_plan.get("status", "unknown") if isinstance(rebalance_plan, dict) else "unknown",
        "masterRebalanceProposed": int(rebalance_summary.get("actions_proposed", 0) or 0),
        "masterRebalanceDeferred": int(rebalance_summary.get("actions_deferred", 0) or 0),
        "masterRebalanceExecutionAllowed": bool(rebalance_plan.get("execution_allowed", False)) if isinstance(rebalance_plan, dict) else False,
        "masterFundingStatus": funding_plan.get("status", "unknown") if isinstance(funding_plan, dict) else "unknown",
        "masterFundingManualApprovalRequired": bool(funding_plan.get("manual_approval_required", True)) if isinstance(funding_plan, dict) else True,
        "masterFundingAutoTransferAllowed": bool(
            (funding_plan.get("inter_universe_transfer", {}) or {}).get("automatic_transfer_allowed", False)
        ) if isinstance(funding_plan, dict) else False,
        "masterFundingByPool": funding_by_pool,
        "apiStatus": "OK",
        "regime": (load_json(PORTFOLIO_TARGET_PATH, default={}) or {}).get(
            "portfolio_regime",
            portfolio_state.get("portfolio_regime", "UNKNOWN"),
        ),
        "governanceMode": "SIMULATED_SAFE" if master_summary.get("governance_action_policy") == "SIMULATED_ONLY" and not bool(master_summary.get("governance_hard_block", False)) and effective_global_status == "OK" and orchestration_status == "OK" else "CAUTION",
        "lastRefresh": utc_now_iso(),
        "capitalObserved": safe_float(portfolio_state.get("capital_observed_eur"), load_initial_capital()),
        "capitalEngaged": safe_float(portfolio_state.get("capital_engaged_eur"), 0.0),
        "cashAvailable": safe_float(portfolio_state.get("cash_available_eur"), 0.0),
        "liveExposureRatio": safe_float(portfolio_state.get("live_exposure_ratio"), 0.0),
        "pnlGlobal": pnl_global,
        "pnlDaily": equity_daily_pnl if equity_daily_pnl is not None else period_pnl.get("pnlDaily"),
        "pnlMTD": equity_mtd_pnl if equity_mtd_pnl is not None else period_pnl.get("pnlMTD"),
        "pnlYTD": equity_ytd_pnl if equity_ytd_pnl is not None else period_pnl.get("pnlYTD"),
        "pnlDailyActive": equity_daily_pnl if equity_daily_pnl is not None else period_pnl.get("pnlDaily"),
        "pnlMTDActive": equity_mtd_pnl if equity_mtd_pnl is not None else period_pnl.get("pnlMTD"),
        "pnlYTDActive": equity_ytd_pnl if equity_ytd_pnl is not None else period_pnl.get("pnlYTD"),
        "drawdown": drawdown_metrics.get("drawdown"),
        "drawdownValue": drawdown_metrics.get("drawdownValue"),
        "drawdownBasis": drawdown_metrics.get("drawdownBasis"),
        "drawdownValidPoints": drawdown_metrics.get("drawdownValidPoints"),
        "pnlShadow": pnl_shadow,
        "pnlLongTerm": pnl_long_term,
        "pnlActiveExShadow": pnl_global,
        "pnlTotalIncludingShadow": pnl_total_including_shadow,
        "pnlTotalIncludingLongTerm": pnl_total_including_long_term,
        "pnlTotalIncludingLongTermAndShadow": pnl_total_including_long_term_and_shadow,
        "openPositionsActive": sum(int(s.get("positions", s.get("openPositions", 0)) or 0) for s in strategies if s.get("stateOrigin")),
        "openPositionsShadow": sum(int(s.get("openPositions", 0) or 0) for s in strategies if not s.get("stateOrigin")),
        "openPositionsTotal": sum(int(s.get("positions", s.get("openPositions", 0)) or 0) for s in strategies),
        "ordersActive": sum(int(s.get("orders", 0) or 0) for s in strategies if s.get("stateOrigin")),
        "ordersSimulated": sum(int(s.get("orders", 0) or 0) for s in strategies if not s.get("stateOrigin")),
        "ordersTotal": sum(int(s.get("orders", 0) or 0) for s in strategies),
        "openPositions": sum(int(s.get("positions", s.get("openPositions", 0)) or 0) for s in strategies),
        "shadowPositions": sum(int(s.get("openPositions", 0) or 0) for s in strategies if not s.get("stateOrigin")),
        "candidatesCount": sum(int(s.get("candidates", 0) or 0) for s in strategies),
        "ordersCount": int(sum(int(s.get("orders", 0) or 0) for s in strategies)),
        "activeEntryOrders": int(sum(
            int(s.get("orders", 0) or 0)
            for s in strategies
            if s.get("key") in ("crypto",)
        )),
        "exitOrders": int(sum(
            int(s.get("orders", 0) or 0)
            for s in strategies
            if s.get("key") in ("equities_offensive",)
        )),
        "shadowOrders": int(sum(
            int(s.get("orders", 0) or 0)
            for s in strategies
            if str(s.get("mode", "")).upper() == "SHADOW"
        )),
        "riskFlags": sum(len(s.get("softVetos", []) or []) for s in strategies),
        "riskFlagsDetails": [
            {
                "strategy": s.get("key"),
                "label": s.get("label"),
                "count": len(s.get("softVetos", []) or []),
                "softVetos": s.get("softVetos", []) or [],
            }
            for s in strategies
            if len(s.get("softVetos", []) or []) > 0
        ],
        "protectedBricksCount": protected_bricks,
        "trailingHitsCount": trailing_hits,
        "protectionLevel": protection_level,
        "protectionSummary": protection_summary,
    }

    return {
        "global": global_payload,
        "equityCurve": {
            "source": str(EQUITY_CURVE_STATE_PATH),
            "generated_at": equity_curve_state.get("generated_at"),
            "history": equity_curve_state.get("history", []),
            "latest": equity_curve_state.get("latest", {}),
        },
        "strategies": strategies,
        "recentActivity": build_recent_activity(),
    }
