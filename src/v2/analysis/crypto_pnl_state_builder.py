from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(os.environ.get("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

EXIT_EVENTS_PATH = DATA_DIR / "trading" / "exit_events.json"
OPEN_POSITIONS_PATH = DATA_DIR / "trading" / "open_positions.json"
PNL_STATE_PATH = DATA_DIR / "analysis" / "pnl_state.json"


def _load_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _num(value, default=0.0) -> float:
    try:
        return float(value or default)
    except Exception:
        return default


def build_crypto_pnl_state() -> dict:
    exits = _load_json(EXIT_EVENTS_PATH, [])
    opens = _load_json(OPEN_POSITIONS_PATH, [])

    if not isinstance(exits, list):
        exits = []
    if not isinstance(opens, list):
        opens = []

    realized = sum(
        _num(e.get("pnl") or e.get("realized_pnl_eur") or e.get("pnl_eur") or 0)
        for e in exits
        if isinstance(e, dict)
    )

    unrealized = sum(
        _num(p.get("unrealized_pnl") or p.get("unrealized_pnl_eur") or 0)
        for p in opens
        if isinstance(p, dict)
    )

    notional = sum(
        _num(p.get("notional_eur") or p.get("notional") or 0)
        for p in opens
        if isinstance(p, dict)
    )

    # Trade statistics must ignore technical cleanup events.
    # stale_plan_cleanup closes paper positions absent from the current plan,
    # but it is not a real strategy exit and should not pollute win rate.
    trade_exits = []
    for e in exits:
        if not isinstance(e, dict):
            continue
        if e.get("exit_type") == "stale_plan_cleanup":
            continue

        pnl = _num(
            e.get("pnl")
            if e.get("pnl") is not None
            else e.get("realized_pnl_eur")
            if e.get("realized_pnl_eur") is not None
            else e.get("pnl_eur")
            if e.get("pnl_eur") is not None
            else 0
        )

        if pnl != 0:
            trade_exits.append({**e, "_normalized_pnl": pnl})

    winning = sum(1 for e in trade_exits if _num(e.get("_normalized_pnl")) > 0)
    losing = sum(1 for e in trade_exits if _num(e.get("_normalized_pnl")) < 0)
    traded = winning + losing

    doc = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "engine": "crypto_pnl_state_builder_v1",
        "source": "exit_events_plus_open_positions",
        "paths": {
            "exit_events": str(EXIT_EVENTS_PATH),
            "open_positions": str(OPEN_POSITIONS_PATH),
        },
        "summary": {
            "realized_pnl_eur": round(realized, 2),
            "unrealized_pnl_eur": round(unrealized, 2),
            "total_pnl_eur": round(realized + unrealized, 2),
            "open_positions_notional_eur": round(notional, 2),
            "open_positions_count": len(opens),
            "simulated_trades_count": traded,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": round((winning / traded) * 100, 2) if traded else 0.0,
            "ignored_cleanup_events": sum(1 for e in exits if isinstance(e, dict) and e.get("exit_type") == "stale_plan_cleanup"),
        },
    }

    PNL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PNL_STATE_PATH.with_suffix(PNL_STATE_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(PNL_STATE_PATH)
    return doc


def main():
    doc = build_crypto_pnl_state()
    print(json.dumps(doc["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
