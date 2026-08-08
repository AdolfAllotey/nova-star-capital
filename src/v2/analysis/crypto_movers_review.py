from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path("/opt/nsc/data/preprod")

SIGNAL_CANDIDATES = BASE / "analysis/signal_candidates.json"
SIGNAL_VOTES = BASE / "analysis/signal_votes.json"
SIZED_SIGNALS = BASE / "trading/sized_signals.json"
EXECUTION_PLAN = BASE / "trading/execution_plan.json"
TRADE_SIMULATION = BASE / "trading/trade_simulation.json"
OPEN_POSITIONS = BASE / "trading/open_positions.json"
PNL_STATE = BASE / "analysis/pnl_state.json"

OUT = BASE / "analysis/crypto_movers_review.json"


def load_json(path: Path, default: Any):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_load_error": str(e)}
    return default


def norm_symbol(x: Any) -> str:
    s = str(x or "").upper().replace("/", "").replace("-", "")
    return s.replace("USDT", "").strip()


def pct(value: Any) -> float:
    try:
        return round(float(value), 4)
    except Exception:
        return 0.0


candidates = load_json(SIGNAL_CANDIDATES, [])
votes = load_json(SIGNAL_VOTES, [])
sized = load_json(SIZED_SIGNALS, [])
execution = load_json(EXECUTION_PLAN, {})
orders = execution.get("orders", []) if isinstance(execution, dict) else []
trades = load_json(TRADE_SIMULATION, [])
open_positions = load_json(OPEN_POSITIONS, [])
pnl_state = load_json(PNL_STATE, {})

candidate_tokens = {norm_symbol(x.get("token") or x.get("symbol")) for x in candidates if isinstance(x, dict)}
order_tokens = {norm_symbol(x.get("token") or x.get("symbol")) for x in orders if isinstance(x, dict)}
open_tokens = {norm_symbol(x.get("token") or x.get("symbol")) for x in open_positions if isinstance(x, dict)}
trade_tokens = {norm_symbol(x.get("token") or x.get("symbol")) for x in trades if isinstance(x, dict)}

current_candidates = []
for x in candidates:
    if not isinstance(x, dict):
        continue
    current_candidates.append({
        "token": norm_symbol(x.get("token") or x.get("symbol")),
        "pair": x.get("pair") or str(x.get("symbol", "")).upper(),
        "strategy": x.get("strategy"),
        "chg_24h": pct(x.get("chg_24h")),
        "meta_score": pct(x.get("meta_score")),
        "momentum_score": pct(x.get("momentum_score")),
        "regime": x.get("momentum_regime"),
        "reason": x.get("reason"),
    })

current_orders = []
for x in orders:
    if not isinstance(x, dict):
        continue
    current_orders.append({
        "token": norm_symbol(x.get("token") or x.get("symbol")),
        "pair": x.get("pair") or str(x.get("symbol", "")).upper(),
        "exchange": x.get("exchange"),
        "action": x.get("action"),
        "execution_mode": x.get("execution_mode"),
        "notional_eur": pct(x.get("notional") or x.get("notional_eur")),
        "risk_flag": x.get("risk_flag"),
        "soft_veto": bool(x.get("soft_veto")),
        "blocked_by": x.get("blocked_by", []),
        "chg_24h": pct(x.get("chg_24h")),
        "meta_score": pct(x.get("meta_score")),
    })

legacy_trades = []
for x in trades:
    if not isinstance(x, dict):
        continue
    legacy_trades.append({
        "token": norm_symbol(x.get("token") or x.get("symbol")),
        "exchange": x.get("exchange"),
        "selection_source": x.get("selection_source"),
        "score": pct(x.get("score")),
        "notional_eur": pct(x.get("notional_eur") or x.get("amount")),
        "pnl_eur": pct(x.get("pnl_eur")),
        "entry_price_eur": pct(x.get("entry_price_eur")),
        "current_price_eur": pct(x.get("current_price_eur")),
    })

open_position_rows = []
for x in open_positions:
    if not isinstance(x, dict):
        continue
    open_position_rows.append({
        "token": norm_symbol(x.get("token") or x.get("symbol")),
        "strategy": x.get("strategy"),
        "notional_eur": pct(x.get("notional_eur")),
        "entry_price": pct(x.get("entry_price")),
        "last_price": pct(x.get("last_price")),
        "unrealized_pnl": pct(x.get("unrealized_pnl")),
        "unrealized_pnl_pct": pct(x.get("unrealized_pnl_pct")),
        "execution_mode": x.get("execution_mode"),
    })

overlap = {
    "candidates_already_open": sorted(candidate_tokens & open_tokens),
    "candidates_already_in_legacy_trades": sorted(candidate_tokens & trade_tokens),
    "orders_already_open": sorted(order_tokens & open_tokens),
    "orders_already_in_legacy_trades": sorted(order_tokens & trade_tokens),
}

diagnosis = []
if current_candidates:
    diagnosis.append(
        f"{len(current_candidates)} market momentum candidates detected: "
        + ", ".join([f"{x['token']} ({x['chg_24h']}%)" for x in current_candidates])
    )

if current_orders:
    diagnosis.append(
        f"{len(current_orders)} simulated orders prepared for a total notional of "
        f"{round(sum(x['notional_eur'] for x in current_orders), 2)} EUR."
    )

if open_position_rows:
    diagnosis.append(
        f"{len(open_position_rows)} open crypto positions remain active: "
        + ", ".join([x["token"] for x in open_position_rows])
    )

if legacy_trades:
    losing = [x for x in legacy_trades if x["pnl_eur"] < 0]
    diagnosis.append(
        f"{len(legacy_trades)} legacy simulated trades tracked, "
        f"{len(losing)} currently negative, total PnL "
        f"{round(sum(x['pnl_eur'] for x in legacy_trades), 2)} EUR."
    )

recommendations = [
    "Comparer ce rapport avec les screenshots top movers/losers du week-end.",
    "Vérifier si les top movers externes apparaissent bien dans signal_candidates.",
    "Identifier les tokens récurrents movers/losers non captés par le moteur crypto.",
    "Contrôler si les tokens retenus sont trop tardifs après un pump > 40-60%.",
    "Ajouter ensuite un fichier manuel crypto_market_highlights_observations.json pour historiser les screenshots.",
]

payload = {
    "status": "ok",
    "engine": "crypto_movers_review_v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "summary": {
        "candidate_count": len(current_candidates),
        "order_count": len(current_orders),
        "open_positions_count": len(open_position_rows),
        "legacy_trades_count": len(legacy_trades),
        "legacy_total_pnl_eur": round(sum(x["pnl_eur"] for x in legacy_trades), 2),
        "open_positions_notional_eur": round(sum(x["notional_eur"] for x in open_position_rows), 2),
    },
    "current_candidates": current_candidates,
    "current_orders": current_orders,
    "open_positions": open_position_rows,
    "legacy_trades": legacy_trades,
    "overlap": overlap,
    "diagnosis": diagnosis,
    "recommendations": recommendations,
    "sources": {
        "signal_candidates": str(SIGNAL_CANDIDATES),
        "signal_votes": str(SIGNAL_VOTES),
        "sized_signals": str(SIZED_SIGNALS),
        "execution_plan": str(EXECUTION_PLAN),
        "trade_simulation": str(TRADE_SIMULATION),
        "open_positions": str(OPEN_POSITIONS),
        "pnl_state": str(PNL_STATE),
    },
}

OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))
