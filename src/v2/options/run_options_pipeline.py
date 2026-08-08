import json
from datetime import datetime, timezone
from pathlib import Path

from engines.volatility_engine import analyze_volatility_context
from engines.options_signal_engine import generate_options_candidates
from risk.options_risk_controller import validate_options_candidates
from execution.options_simulator import simulate_options_candidates
from monitoring.options_telemetry import build_options_metrics

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "options_pipeline.log"
INPUTS_FILE = DATA_DIR / "options_inputs.json"
CONFIG_FILE = DATA_DIR / "options_config.json"
STATUS_FILE = DATA_DIR / "options_status.json"
VOL_CONTEXT_FILE = DATA_DIR / "volatility_context.json"
RAW_CANDIDATES_FILE = DATA_DIR / "options_candidates_raw.json"
VALIDATED_CANDIDATES_FILE = DATA_DIR / "options_candidates_validated.json"
POSITIONS_FILE = DATA_DIR / "options_positions.json"
TRADES_FILE = DATA_DIR / "options_trades.json"
METRICS_FILE = DATA_DIR / "options_metrics.json"

EXTERNAL_EQUITY_POSITIONS_FILE = DATA_DIR / "external_equity_positions.json"
EXTERNAL_WATCHLISTS_FILE = DATA_DIR / "external_watchlists.json"
EXTERNAL_SIGNALS_FILE = DATA_DIR / "external_signals.json"

OPTIONS_VERSION = "v1.0.0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    line = f"{utc_now_iso()} | INFO | options_pipeline | {message}"
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
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"Erreur écriture JSON {path}: {e}")
        raise


def build_default_inputs():
    return {
        "ts": utc_now_iso(),
        "capital": {
            "total_capital_eur": 100000.0,
            "max_capital_per_trade_pct": 0.02,
            "max_total_options_exposure_pct": 0.15,
            "max_open_positions": 5
        },
        "governance": {
            "allowed_strategies": [
                "covered_call",
                "cash_secured_put",
                "vertical_spread"
            ],
            "block_near_events": True,
            "event_block_window_days": 5,
            "min_confidence_by_strategy": {
                "covered_call": 0.70,
                "cash_secured_put": 0.65,
                "vertical_spread": 0.70
            },
            "covered_call_requires_sell_vol": True,
            "cash_secured_put_requires_sell_vol": True,
            "vertical_spread_allow_buy_or_neutral_vol": True
        },
        "positions": [
            {
                "ticker": "KO",
                "type": "equity",
                "quantity": 100,
                "avg_price": 58.0,
                "current_price": 60.0,
                "style": "defensive"
            },
            {
                "ticker": "JNJ",
                "type": "equity",
                "quantity": 100,
                "avg_price": 145.0,
                "current_price": 148.0,
                "style": "defensive"
            }
        ],
        "watchlists": {
            "defensive": ["KO", "JNJ", "PG", "PEP"],
            "offensive": ["AAPL", "MSFT", "NVDA", "AMD"]
        },
        "signals": [
            {
                "ticker": "NVDA",
                "signal_type": "offensive",
                "direction": "bullish",
                "confidence": 0.81,
                "setup": "continuation",
                "spot": 920.0
            },
            {
                "ticker": "MSFT",
                "signal_type": "watchlist_entry",
                "direction": "neutral_to_bullish",
                "confidence": 0.74,
                "setup": "quality_pullback",
                "spot": 420.0
            },
            {
                "ticker": "KO",
                "signal_type": "portfolio_overlay",
                "direction": "neutral",
                "confidence": 0.77,
                "setup": "income_overlay",
                "spot": 60.0
            }
        ],
        "volatility_data": {
            "KO": {
                "iv": 0.24,
                "iv_rank": 61,
                "historical_vol": 0.16,
                "days_to_event": 30
            },
            "JNJ": {
                "iv": 0.22,
                "iv_rank": 55,
                "historical_vol": 0.15,
                "days_to_event": 40
            },
            "MSFT": {
                "iv": 0.29,
                "iv_rank": 68,
                "historical_vol": 0.22,
                "days_to_event": 21
            },
            "NVDA": {
                "iv": 0.43,
                "iv_rank": 64,
                "historical_vol": 0.36,
                "days_to_event": 18
            }
        },
        "notes": "Options V1 isolated sandbox bootstrap"
    }


def build_default_config():
    return {
        "options_enabled": True,
        "mode": "SIMULATION",
        "simulation": {
            "min_hours_between_marks": 24,
            "default_take_profit_pct": 75.0,
            "default_stop_loss_pct": -50.0
        },
        "input_sources": {
            "use_external_positions": True,
            "use_external_watchlists": True,
            "use_external_signals": True
        }
    }


def ensure_inputs():
    if not INPUTS_FILE.exists():
        inputs = build_default_inputs()
        save_json_file(INPUTS_FILE, inputs)
        log("options_inputs.json initialisé.")
        return inputs
    inputs = load_json_file(INPUTS_FILE, default={})
    log("options_inputs.json chargé.")
    return inputs


def ensure_config():
    if not CONFIG_FILE.exists():
        config = build_default_config()
        save_json_file(CONFIG_FILE, config)
        log("options_config.json initialisé.")
        return config
    config = load_json_file(CONFIG_FILE, default={})
    log("options_config.json chargé.")
    return config


def resolve_positions(inputs, input_sources):
    use_external = bool(input_sources.get("use_external_positions", False))
    if use_external and EXTERNAL_EQUITY_POSITIONS_FILE.exists():
        data = load_json_file(EXTERNAL_EQUITY_POSITIONS_FILE, default=[])
        return data, "external_equity_positions.json"
    return inputs.get("positions", []), "options_inputs.json:positions"


def resolve_watchlists(inputs, input_sources):
    use_external = bool(input_sources.get("use_external_watchlists", False))
    if use_external and EXTERNAL_WATCHLISTS_FILE.exists():
        data = load_json_file(EXTERNAL_WATCHLISTS_FILE, default={})
        return data, "external_watchlists.json"
    return inputs.get("watchlists", {}), "options_inputs.json:watchlists"


def resolve_signals(inputs, input_sources):
    use_external = bool(input_sources.get("use_external_signals", False))
    if use_external and EXTERNAL_SIGNALS_FILE.exists():
        data = load_json_file(EXTERNAL_SIGNALS_FILE, default=[])
        return data, "external_signals.json"
    return inputs.get("signals", []), "options_inputs.json:signals"


def main() -> None:
    log(f"===== START OPTIONS PIPELINE {OPTIONS_VERSION} =====")

    inputs = ensure_inputs()
    config = ensure_config()

    options_enabled = bool(config.get("options_enabled", True))
    mode = config.get("mode", "SIMULATION")
    simulation_config = config.get("simulation", {})
    input_sources = config.get("input_sources", {})

    if not options_enabled:
        log("Brique options désactivée.")
        status = {
            "ts": utc_now_iso(),
            "module": "options_pipeline",
            "version": OPTIONS_VERSION,
            "status": "disabled",
            "mode": mode,
            "options_enabled": False,
            "message": "Brique options désactivée par configuration."
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
    log("volatility_context.json généré.")

    raw_candidates = generate_options_candidates(
        signals=signals_source_data,
        positions=positions_source_data,
        watchlists=watchlists_source_data,
        volatility_context=vol_context,
        governance=governance,
    )
    save_json_file(RAW_CANDIDATES_FILE, raw_candidates)
    log("options_candidates_raw.json généré.")

    existing_positions = load_json_file(POSITIONS_FILE, default=[])
    existing_trades = load_json_file(TRADES_FILE, default=[])

    validated_candidates = validate_options_candidates(
        candidates=raw_candidates,
        capital_config=inputs.get("capital", {}),
        governance=governance,
        existing_positions=existing_positions,
    )
    save_json_file(VALIDATED_CANDIDATES_FILE, validated_candidates)
    log("options_candidates_validated.json généré.")

    simulated_positions, trades = simulate_options_candidates(
        validated_candidates=validated_candidates,
        existing_positions=existing_positions,
        existing_trades=existing_trades,
        mode=mode,
        simulation_config=simulation_config,
    )
    save_json_file(POSITIONS_FILE, simulated_positions)
    save_json_file(TRADES_FILE, trades)
    log("options_positions.json généré.")
    log("options_trades.json généré.")

    metrics = build_options_metrics(
        positions=simulated_positions,
        trades=trades,
        candidates=validated_candidates,
    )
    save_json_file(METRICS_FILE, metrics)
    log("options_metrics.json généré.")

    approved_count = len([
        c for c in validated_candidates
        if c.get("risk_validation", {}).get("approved", False)
    ])

    open_positions_count = len([
        p for p in simulated_positions
        if p.get("status") == "OPEN"
    ])

    status = {
        "ts": utc_now_iso(),
        "module": "options_pipeline",
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
        "trades_count": len(trades),
        "min_hours_between_marks": int(simulation_config.get("min_hours_between_marks", 24)),
        "message": "Pipeline Options V1 finalized and preprod-ready."
    }
    save_json_file(STATUS_FILE, status)

    log("options_status.json généré.")
    log(f"===== END OPTIONS PIPELINE {OPTIONS_VERSION} =====")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Erreur fatale: {e}")
        raise
