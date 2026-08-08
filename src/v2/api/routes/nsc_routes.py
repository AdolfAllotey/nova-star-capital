# -*- coding: utf-8 -*-
# src/v2/api/routes/nsc_routes.py

from __future__ import annotations

import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter

from src.v2.utils.file_utils import get_data_dir

router = APIRouter()

DATA = Path(get_data_dir())

REPORTS_DIR = DATA / "reports"
RISK_DIR = DATA / "risk"
TRADING_DIR = DATA / "trading"
ANALYSIS_DIR = DATA / "analysis"
SIGNALS_DIR = DATA / "signals"
SYSTEM_DIR = DATA / "system"

TRADE_SIM_FILE = REPORTS_DIR / "trade_simulation.json"
OPEN_POS_FILE = TRADING_DIR / "open_positions.json"
EXIT_EVENTS_FILE = TRADING_DIR / "exit_events.json"
PNL_SERIES_FILE = REPORTS_DIR / "pnl_series.json"

MARKET_REGIME_FILE = ANALYSIS_DIR / "market_regime_detector.json"
MARKET_REGIME_FILE_FALLBACK = REPORTS_DIR / "market_regime.json"

SENTIMENT_FILE = REPORTS_DIR / "average_sentiment.json"
SENTIMENT_FILE_FALLBACK = DATA / "average_sentiment.json"
MOMENTUM_FILE = REPORTS_DIR / "average_momentum.json"

SYSTEM_INFO_FILE = SYSTEM_DIR / "system_info.json"

WORST_TRADES_FILE = RISK_DIR / "worst_trades.json"
WORST_TRADES_SUMMARY_FILE = RISK_DIR / "worst_trades_summary.json"

WHALES_FILE = SIGNALS_DIR / "whales.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists() and path.stat().st_size > 0:
            import json
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def ensure_number(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def coerce_iso8601(s: Optional[str]) -> str:
    if not s:
        return iso_now()
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return iso_now()


@router.get("/dashboard/market_regime")
def dashboard_market_regime():
    d = load_json(MARKET_REGIME_FILE, {})
    if not isinstance(d, dict) or not d:
        d = load_json(MARKET_REGIME_FILE_FALLBACK, {})

    regime = (d.get("regime") or d.get("label") or "NEUTRAL").upper()
    score = ensure_number(d.get("score", d.get("confidence", d.get("aggregate_score", 0.0))))
    date = coerce_iso8601(d.get("date") or d.get("ts"))
    return {
        "regime": regime,
        "score": score,
        "confidence": score,
        "status": d.get("status", "ok"),
        "date": date,
        "reasons": d.get("reasons", []),
        "inputs": d.get("inputs", {}),
        "components": d.get("components", {}),
        "data_quality": d.get("data_quality"),
        "raw_score": d.get("raw_score"),
        "source": d.get("source", "market_regime_detector")
    }
@router.get("/trades/open")
def trades_open():
    trades = load_json(TRADE_SIM_FILE, [])
    if not isinstance(trades, list):
        trades = []
    open_trades = [t for t in trades if str(t.get("status") or "").lower() in ("open", "ongoing", "running")]
    return {"trades": open_trades}


@router.get("/trades/history")
def trades_history():
    trades = load_json(TRADE_SIM_FILE, [])
    if not isinstance(trades, list):
        trades = []
    closed = [t for t in trades if str(t.get("status") or "").lower() in ("closed", "done", "exit", "exited")]
    return {"trades": closed}


@router.get("/portfolio/open")
def portfolio_open():
    positions = load_json(OPEN_POS_FILE, [])
    if not isinstance(positions, list):
        positions = []
    return {"positions": positions}


@router.get("/signals/whales")
def signals_whales():
    events = load_json(WHALES_FILE, [])
    if not isinstance(events, list):
        events = []
    return {"events": events}


@router.get("/risk/worst")
def risk_worst():
    w = load_json(WORST_TRADES_FILE, [])

    if isinstance(w, dict):
        trades = (
            w.get("trades")
            or w.get("worst_trades")
            or w.get("items")
            or []
        )
    elif isinstance(w, list):
        trades = w
    else:
        trades = []

    if not isinstance(trades, list):
        trades = []

    return {
        "status": "ok",
        "count": len(trades),
        "trades": trades,
        "worst_trades": trades,
    }


@router.get("/risk/worst-trades")
def risk_worst_trades_alias():
    return risk_worst()


@router.get("/risk/worst/summary")
def risk_worst_summary():
    s = load_json(WORST_TRADES_SUMMARY_FILE, "")
    if isinstance(s, dict):
        return s
    return {"summary": str(s) if s else "—"}


@router.get("/risk/worst-trades/summary")
def risk_worst_trades_summary_alias():
    return risk_worst_summary()

# ---------------------------------------------------------------------
# NSC Explainability V6
# ---------------------------------------------------------------------
@router.get("/api/explainability")
def get_explainability_v6():
    return explainability_v6_response()

    from pathlib import Path
    import json
    from datetime import datetime, timezone

    base = Path("/opt/nsc/data/preprod")

    def load(path, default):
        try:
            p = Path(path)
            if p.exists() and p.stat().st_size > 0:
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default

    market = load(base / "analysis" / "market_regime_detector.json", {})
    risk = load(base / "trading" / "risk_limits.json", {})
    perf = load(base / "analysis" / "strategy_performance.json", {})
    weights = load(base / "analysis" / "strategy_weights.json", {})

    regime = str(market.get("regime", "unknown")).upper()
    score = market.get("score", market.get("confidence"))
    components = market.get("components", {})
    strategy_factors = risk.get("strategy_intensity_factors", {})
    strategy_vetos = risk.get("strategy_vetos", {})
    strategy_boosts = risk.get("strategy_boosts", {})
    selector_diag = weights.get("diagnostics", {})
    by_strategy = perf.get("by_strategy", {})

    narrative = []
    narrative.append(f"Market regime is {regime} with confidence {score}.")
    if components:
        narrative.append(
            f"Trend={components.get('trend')}, volatility={components.get('volatility')}, "
            f"breadth={components.get('breadth')}, macro={components.get('macro')}."
        )
    if strategy_boosts:
        narrative.append("Some strategies are currently allowed or boosted based on regime context.")
    if strategy_vetos:
        narrative.append("Some strategies are vetoed by governance/risk context.")
    if risk.get("risk_console_flag"):
        narrative.append(f"Risk console flag is {risk.get('risk_console_flag')}.")

    return {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "engine": "explainability_v6",
        "status": "ready",
        "market_regime": market,
        "risk_limits": {
            "risk_console_flag": risk.get("risk_console_flag"),
            "risk_mode": risk.get("risk_mode"),
            "size_factor": risk.get("size_factor"),
            "max_positions": risk.get("max_positions"),
            "strategy_intensity_factors": strategy_factors,
            "strategy_vetos": strategy_vetos,
            "strategy_boosts": strategy_boosts,
            "strategy_intensity_context": risk.get("strategy_intensity_context", {}),
        },
        "strategy_performance": by_strategy,
        "strategy_selector": {
            "weights": weights.get("weights", {}),
            "diagnostics": selector_diag,
        },
        "narrative": narrative,
    }

# ---------------------------------------------------------------------
# NSC Explainability V6
# ---------------------------------------------------------------------
@router.get("/api/explainability")
def get_explainability_v6():
    return explainability_v6_response()

    from pathlib import Path
    import json
    from datetime import datetime, timezone

    base = Path("/opt/nsc/data/preprod")

    def load(path, default):
        try:
            p = Path(path)
            if p.exists() and p.stat().st_size > 0:
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default

    market = load(base / "analysis" / "market_regime_detector.json", {})
    risk = load(base / "trading" / "risk_limits.json", {})
    perf = load(base / "analysis" / "strategy_performance.json", {})
    weights = load(base / "analysis" / "strategy_weights.json", {})

    regime = str(market.get("regime", "unknown")).upper()
    score = market.get("score", market.get("confidence"))
    components = market.get("components", {})
    strategy_factors = risk.get("strategy_intensity_factors", {})
    strategy_vetos = risk.get("strategy_vetos", {})
    strategy_boosts = risk.get("strategy_boosts", {})
    selector_diag = weights.get("diagnostics", {})
    by_strategy = perf.get("by_strategy", {})

    narrative = []
    narrative.append(f"Market regime is {regime} with confidence {score}.")
    if components:
        narrative.append(
            f"Trend={components.get('trend')}, volatility={components.get('volatility')}, "
            f"breadth={components.get('breadth')}, macro={components.get('macro')}."
        )
    if strategy_boosts:
        narrative.append("Some strategies are currently allowed or boosted based on regime context.")
    if strategy_vetos:
        narrative.append("Some strategies are vetoed by governance/risk context.")
    if risk.get("risk_console_flag"):
        narrative.append(f"Risk console flag is {risk.get('risk_console_flag')}.")

    return {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "engine": "explainability_v6",
        "status": "ready",
        "market_regime": market,
        "risk_limits": {
            "risk_console_flag": risk.get("risk_console_flag"),
            "risk_mode": risk.get("risk_mode"),
            "size_factor": risk.get("size_factor"),
            "max_positions": risk.get("max_positions"),
            "strategy_intensity_factors": strategy_factors,
            "strategy_vetos": strategy_vetos,
            "strategy_boosts": strategy_boosts,
            "strategy_intensity_context": risk.get("strategy_intensity_context", {}),
        },
        "strategy_performance": by_strategy,
        "strategy_selector": {
            "weights": weights.get("weights", {}),
            "diagnostics": selector_diag,
        },
        "narrative": narrative,
    }


def explainability_v6_response():
    from pathlib import Path
    import json

    base = Path("/opt/nsc/data/preprod")

    def load(p):
        try:
            if p.exists():
                return json.loads(p.read_text())
        except:
            pass
        return {}

    regime = load(base / "analysis/market_regime_detector.json")
    risk = load(base / "trading/risk_limits.json")
    perf = load(base / "analysis/strategy_performance.json")
    selector = load(base / "analysis/strategy_weights.json")

    return {
        "status": "ok",
        "engine": "explainability_v6",
        "market_regime": regime.get("regime"),
        "market_score": regime.get("score"),
        "risk_flag": risk.get("effective_nsc_mode"),
        "size_factor": risk.get("size_factor"),
        "max_positions": risk.get("max_positions"),
        "selector_weights": selector.get("weights"),
        "strategy_reasoning": risk.get("strategy_intensity_context"),
        "strategy_performance": perf.get("by_strategy"),
        "narrative": "Market regime driven allocation with risk-controlled execution"
    }

