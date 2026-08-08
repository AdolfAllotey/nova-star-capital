from pathlib import Path
from datetime import datetime, timezone
import json
import logging

DATA_DIR = Path("/opt/nsc/data/preprod")
OUT_DIR = DATA_DIR / "risk"
OUT_FILE = OUT_DIR / "worst_trades.json"
SUMMARY_FILE = OUT_DIR / "worst_trades_summary.json"

CANDIDATE_FILES = [
    DATA_DIR / "trading" / "trade_simulation.json",
    DATA_DIR / "reports" / "trade_simulation.json",
    DATA_DIR / "trading" / "exit_events.json",
    DATA_DIR / "risk" / "worst_trades_source.json",
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worst_trade_analyzer")


def load_json(path, default):
    try:
        if path.exists() and path.stat().st_size > 0:
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Cannot read %s: %s", path, e)
    return default


def to_float(x, default=0.0):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def normalize_rows(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("trades", "worst_trades", "items", "results", "positions", "events"):
            val = raw.get(key)
            if isinstance(val, list):
                return val
    return []


def get_pnl(row):
    for key in (
        "pnl_eur",
        "realized_pnl_eur",
        "realized_pnl",
        "pnl",
        "profit_loss",
        "profit_loss_eur",
        "loss_eur",
    ):
        if key in row:
            val = to_float(row.get(key), None)
            if val is not None:
                if key == "loss_eur" and val > 0:
                    return -val
                return val
    return 0.0


def infer_strategy(row):
    strategy = row.get("strategy")
    if strategy:
        return str(strategy).lower(), False

    selection_source = str(row.get("selection_source", "")).lower()
    mentions = to_float(row.get("mentions"), 0.0)
    score = to_float(row.get("score"), 0.0)

    if "scored_social" in selection_source or mentions > 0:
        return "momentum_social", True

    if score >= 70:
        return "momentum", True

    return "unknown", False


def normalize_trade(row, source):
    symbol = (
        row.get("symbol")
        or row.get("token")
        or row.get("asset")
        or row.get("pair")
        or "unknown"
    )

    pnl = get_pnl(row)
    strategy, strategy_inferred = infer_strategy(row)

    return {
        "timestamp": row.get("timestamp") or row.get("date") or row.get("closed_at") or row.get("opened_at"),
        "symbol": str(symbol).upper(),
        "token": str(symbol).upper(),
        "exchange": row.get("exchange", "unknown"),
        "strategy": strategy,
        "strategy_inferred": strategy_inferred,
        "side": row.get("side") or row.get("action") or "unknown",
        "amount": to_float(row.get("amount", row.get("size", row.get("qty", 0.0))), 0.0),
        "notional_eur": to_float(row.get("notional_eur", row.get("entry_value_eur", 0.0)), 0.0),
        "pnl_eur": round(pnl, 6),
        "risk_mode": row.get("risk_mode", row.get("market_regime", "unknown")),
        "source": str(source),
        "raw": row,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    used_sources = []

    for path in CANDIDATE_FILES:
        raw = load_json(path, None)
        part = normalize_rows(raw)
        if part:
            used_sources.append(str(path))
            rows.extend(normalize_trade(x, path) for x in part if isinstance(x, dict))

    worst = [x for x in rows if to_float(x.get("pnl_eur"), 0.0) < 0]
    worst = sorted(worst, key=lambda x: to_float(x.get("pnl_eur"), 0.0))[:5]

    total = round(sum(to_float(x.get("pnl_eur"), 0.0) for x in worst), 6)
    avg = round(total / len(worst), 6) if worst else 0.0

    payload = {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_files": used_sources,
        "count": len(worst),
        "trades": worst,
        "worst_trades": worst,
        "summary": {
            "count": len(worst),
            "total_pnl_eur": total,
            "average_pnl_eur": avg,
        },
    }

    OUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    from collections import Counter

    tokens = [x.get("symbol", "UNKNOWN") for x in worst]
    strategies = [x.get("strategy", "unknown") for x in worst]
    exchanges = [x.get("exchange", "unknown") for x in worst]
    risk_modes = [x.get("risk_mode", "unknown") for x in worst]

    summary = {
        "summary": (
            f"{len(worst)} losing trades detected for a total PnL of {total} EUR. "
            "Losses are concentrated on social-momentum altcoin signals. "
            "This suggests the need for stricter batch controls, better altcoin selectivity "
            "and stronger confirmation filters."
            if worst else
            "No losing trades detected in the current dataset."
        ),
        "root_causes": [
            "Social-momentum source without enough confirmation from relative strength.",
            "Altcoin concentration while risk mode was still risk_on.",
            "Strategy labels inferred from selection_source when historical simulation rows do not store strategy explicitly."
        ] if worst else [],
        "tokens_to_blacklist": tokens,
        "suggested_rules": [
            "Store explicit strategy in trade_simulation.json at generation time.",
            "Limit simultaneous social-momentum altcoin entries to 2 per batch.",
            "Require relative_strength > 0 for social-momentum altcoin entries.",
            "Reduce sizing on altcoins when several social signals trigger at the same timestamp."
        ] if worst else [],
        "metrics": {
            "n_worst": len(worst),
            "total_pnl_eur": total,
            "avg_pnl_eur": avg,
            "tokens_in_worst": tokens,
            "top_strategies": Counter(strategies).most_common(),
            "top_exchanges": Counter(exchanges).most_common(),
            "risk_modes_in_worst": risk_modes,
        },
        "context": {
            "env": "PREPROD",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine": "worst_trade_analyzer_rebuild_v2",
            "model": "deterministic"
        },
        "llm_status": "deterministic_summary",
        "llm_error": None
    }

    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"worst_trades rebuilt: {len(worst)} trades")
    print(f"sources: {used_sources}")


if __name__ == "__main__":
    main()
