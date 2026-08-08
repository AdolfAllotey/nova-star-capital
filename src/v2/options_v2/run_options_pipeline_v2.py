from options_snapshot_v2 import build_snapshot, save_snapshot, append_snapshot_history
from options_rejection_stats_v2 import update_rejection_stats
from options_advanced_stats_v2 import generate_advanced_stats
from options_leaderboard_v2 import generate_leaderboard
from options_daily_report_v2 import generate_daily_report
from options_dashboard_export_v2 import generate_dashboard_export
from pathlib import Path
import json

DECISIONS_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_decisions.json")

def save_decisions(decisions):
    DECISIONS_PATH.write_text(
        json.dumps(decisions, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
SRC_V2_DIR = BASE_DIR.parent
if str(SRC_V2_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_V2_DIR))

from options_v2.engines.volatility_engine import analyze_volatility_context
from options_v2.engines.options_signal_engine import generate_options_candidates
from options_v2.risk.options_risk_controller import validate_options_candidates
from options_v2.execution.options_simulator_v2 import simulate_options_candidates_v2
from options_v2.monitoring.options_telemetry_v2 import build_options_metrics_v2

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = SRC_V2_DIR / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "options_pipeline_v2.log"

INPUTS_FILE = SRC_V2_DIR / "options" / "data" / "options_inputs.json"
CONFIG_FILE = DATA_DIR / "options_config_v2.json"

STATUS_FILE = DATA_DIR / "options_v2_status.json"
VOL_CONTEXT_FILE = DATA_DIR / "volatility_context_v2.json"
RAW_CANDIDATES_FILE = DATA_DIR / "options_v2_candidates_raw.json"
VALIDATED_CANDIDATES_FILE = DATA_DIR / "options_v2_candidates_validated.json"
POSITIONS_FILE = DATA_DIR / "options_v2_positions.json"
TRADES_FILE = DATA_DIR / "options_v2_trades.json"
METRICS_FILE = DATA_DIR / "options_v2_metrics.json"

DECISIONS_FILE = DATA_DIR / "options_v2_decisions.json"


def save_decisions_file(path: Path, decisions) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2, ensure_ascii=False)


EXTERNAL_EQUITY_POSITIONS_FILE = SRC_V2_DIR / "options" / "data" / "external_equity_positions.json"
EXTERNAL_WATCHLISTS_FILE = SRC_V2_DIR / "options" / "data" / "external_watchlists.json"
EXTERNAL_SIGNALS_FILE = SRC_V2_DIR / "options" / "data" / "external_signals.json"

OPTIONS_VERSION = "v2.0.0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    line = f"{utc_now_iso()} | INFO | options_pipeline_v2 | {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json_file(path: Path, default):
    try:
        if not path.exists():
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Erreur lecture JSON {path}: {e}")
        return default


def save_json_file(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_default_config():
    return {
        "options_enabled": True,
        "mode": "SIMULATION",
        "simulation": {
            "min_hours_between_marks": 24,
            "default_take_profit_pct": 50.0,
            "default_stop_loss_pct": -50.0,
            "force_close_days_to_expiry": 5,
            "base_theta_daily": 0.01,
            "vol_impact_weight": 0.15,
            "directional_weight_vertical": 0.45,
            "directional_weight_short_premium": 0.15
        },
        "market_context": {
            "global_regime": "neutral"
        },
        "input_sources": {
            "use_external_positions": True,
            "use_external_watchlists": True,
            "use_external_signals": True
        }
    }


def ensure_config():
    if not CONFIG_FILE.exists():
        config = build_default_config()
        save_json_file(CONFIG_FILE, config)
        log("options_config_v2.json initialisé.")
        return config
    config = load_json_file(CONFIG_FILE, default={})
    log("options_config_v2.json chargé.")
    return config


def resolve_positions(inputs, input_sources):
    if bool(input_sources.get("use_external_positions", False)) and EXTERNAL_EQUITY_POSITIONS_FILE.exists():
        return load_json_file(EXTERNAL_EQUITY_POSITIONS_FILE, default=[]), "external_equity_positions.json"
    return inputs.get("positions", []), "options_inputs.json:positions"


def resolve_watchlists(inputs, input_sources):
    if bool(input_sources.get("use_external_watchlists", False)) and EXTERNAL_WATCHLISTS_FILE.exists():
        return load_json_file(EXTERNAL_WATCHLISTS_FILE, default={}), "external_watchlists.json"
    return inputs.get("watchlists", {}), "options_inputs.json:watchlists"


def resolve_signals(inputs, input_sources):
    if bool(input_sources.get("use_external_signals", False)) and EXTERNAL_SIGNALS_FILE.exists():
        return load_json_file(EXTERNAL_SIGNALS_FILE, default=[]), "external_signals.json"
    return inputs.get("signals", []), "options_inputs.json:signals"


def main() -> None:
    log(f"===== START OPTIONS PIPELINE {OPTIONS_VERSION} =====")
    decisions = []

    inputs = load_json_file(INPUTS_FILE, default={})
    log("options_inputs.json chargé.")
    config = ensure_config()

    options_enabled = bool(config.get("options_enabled", True))
    mode = config.get("mode", "SIMULATION")
    simulation_config = config.get("simulation", {})
    market_context = config.get("market_context", {})
    input_sources = config.get("input_sources", {})

    if not options_enabled:
        status = {
            "ts": utc_now_iso(),
            "module": "options_pipeline_v2",
            "version": OPTIONS_VERSION,
            "status": "disabled",
            "mode": mode,
            "options_enabled": False,
            "message": "Brique options V2 désactivée."
        }
        save_json_file(STATUS_FILE, status)
        return

    governance = inputs.get("governance", {})
    volatility_data = inputs.get("volatility_data", {})

    positions_source_data, positions_source_name = resolve_positions(inputs, input_sources)
    watchlists_source_data, watchlists_source_name = resolve_watchlists(inputs, input_sources)
    signals_source_data, signals_source_name = resolve_signals(inputs, input_sources)

    vol_context = analyze_volatility_context(
        volatility_data=volatility_data,
        governance=governance,
    )
    save_json_file(VOL_CONTEXT_FILE, vol_context)
    log("volatility_context_v2.json généré.")

    raw_candidates = generate_options_candidates(
        signals=signals_source_data,
        positions=positions_source_data,
        watchlists=watchlists_source_data,
        volatility_context=vol_context,
        governance=governance,
    )
    save_json_file(RAW_CANDIDATES_FILE, raw_candidates)
    log("options_v2_candidates_raw.json généré.")

    existing_positions = load_json_file(POSITIONS_FILE, default=[])
    existing_trades = load_json_file(TRADES_FILE, default=[])

    open_keys = {
        f"{p.get('ticker')}|{p.get('strategy')}|OPEN"
        for p in existing_positions
        if p.get("status") == "OPEN"
    }

    cooldown_hours_after_close = int(simulation_config.get("cooldown_hours_after_close", 0))

    def _parse_ts(ts):
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return None

    def _recently_closed_same_trade(trades, ticker, strategy, cooldown_hours):
        if cooldown_hours <= 0:
            return False
        now = datetime.now(timezone.utc)
        for trade in reversed(trades):
            if trade.get("action") != "CLOSE":
                continue
            if trade.get("ticker") != ticker:
                continue
            if trade.get("strategy") != strategy:
                continue
            ts = _parse_ts(trade.get("ts"))
            if ts is None:
                continue
            delta = now - ts
            return delta.total_seconds() < cooldown_hours * 3600
        return False

    validated_candidates = validate_options_candidates(
        candidates=raw_candidates,
        capital_config=inputs.get("capital", {}),
        governance=governance,
        existing_positions=existing_positions,
    )
    save_json_file(VALIDATED_CANDIDATES_FILE, validated_candidates)
    log("options_v2_candidates_validated.json généré.")

    for candidate in validated_candidates:
        ticker = candidate.get("ticker")
        strategy = candidate.get("strategy")
        approved_signal = bool(candidate.get("approved_signal", False))
        approved_risk = bool(candidate.get("risk_validation", {}).get("approved", False))

        decision = {
            "ts": utc_now_iso(),
            "ticker": ticker,
            "strategy": strategy,
            "status": None,
            "reason": None,
        }

        if not approved_signal:
            decision["status"] = "REJECTED_SIGNAL"
            decision["reason"] = candidate.get("blocked_reason", "signal_not_approved")
        elif not approved_risk:
            decision["status"] = "REJECTED_RISK"
            decision["reason"] = candidate.get("risk_validation", {}).get("reason", "risk_validation_failed")
        elif f"{ticker}|{strategy}|OPEN" in open_keys:
            decision["status"] = "REJECTED_COOLDOWN"
            decision["reason"] = "already_open_position"
        elif _recently_closed_same_trade(existing_trades, ticker, strategy, cooldown_hours_after_close):
            decision["status"] = "REJECTED_COOLDOWN"
            decision["reason"] = "cooldown_after_close"
        else:
            decision["status"] = "APPROVED"
            decision["reason"] = "passed_all_checks"

        decisions.append(decision)

    save_decisions_file(DECISIONS_FILE, decisions)
    log("options_v2_decisions.json généré.")
    update_rejection_stats()
    log("options_v2_rejection_stats.json généré.")

    simulated_positions, trades = simulate_options_candidates_v2(
        validated_candidates=validated_candidates,
        existing_positions=existing_positions,
        existing_trades=existing_trades,
        mode=mode,
        simulation_config=simulation_config,
        market_context=market_context,
    )
    save_json_file(POSITIONS_FILE, simulated_positions)
    save_json_file(TRADES_FILE, trades)
    log("options_v2_positions.json généré.")
    log("options_v2_trades.json généré.")

    metrics = build_options_metrics_v2(
        positions=simulated_positions,
        trades=trades,
        candidates=validated_candidates,
    )
    save_json_file(METRICS_FILE, metrics)
    log("options_v2_metrics.json généré.")
    generate_advanced_stats()
    log("options_v2_advanced_stats.json généré.")
    generate_leaderboard()
    log("options_v2_leaderboard.json généré.")
    generate_daily_report()
    log("options_v2_daily_report.json généré.")
    generate_dashboard_export()
    log("options_v2_dashboard.json généré.")

    approved_count = len([c for c in validated_candidates if c.get("risk_validation", {}).get("approved", False)])
    open_positions_count = len([p for p in simulated_positions if p.get("status") == "OPEN"])
    closed_positions_count = len([p for p in simulated_positions if p.get("status") == "CLOSED"])
    close_trades_count = len([t for t in trades if t.get("action") == "CLOSE"])

    status = {
        "ts": utc_now_iso(),
        "module": "options_pipeline_v2",
        "version": OPTIONS_VERSION,
        "status": "ok",
        "mode": mode,
        "options_enabled": options_enabled,
        "input_sources": {
            "positions": positions_source_name,
            "watchlists": watchlists_source_name,
            "signals": signals_source_name,
            "volatility_data": "options_inputs.json:volatility_data"
        },
        "raw_candidates_count": len(raw_candidates),
        "validated_candidates_count": len(validated_candidates),
        "approved_candidates_count": approved_count,
        "open_positions_count": open_positions_count,
        "closed_positions_count": closed_positions_count,
        "trades_count": len(trades),
        "close_trades_count": close_trades_count,
        "min_hours_between_marks": int(simulation_config.get("min_hours_between_marks", 24)),
        "message": "Pipeline Options V2 ready."
    }
    save_json_file(STATUS_FILE, status)


    snapshot = build_snapshot()
    save_snapshot(snapshot)
    append_snapshot_history(snapshot)


    log("options_v2_status.json généré.")
    log(f"===== END OPTIONS PIPELINE {OPTIONS_VERSION} =====")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Erreur fatale: {e}")
        raise
